"""Lo que se suma a los observatorios con los ejes temáticos: indicadores nuevos, ajustes a los existentes, el
catálogo de fuentes, las conexiones automáticas y los visores de otras instituciones.

Todos los valores se leyeron en su fuente el 5 de octubre de 2026 (informes de investigación en la sesión de trabajo):
los «calculados» dividen dos cifras de la misma tabla oficial y lo dicen en su nota; los que la fuente marca como
preliminares van como provisionales. Nada se estima. Los umbrales de alerta citan la norma o la clasificación de
donde salen (OMS, UNICEF, Ministerio de Agricultura).
"""
from apps.observatorios.operacion.management.observatorios.contenidos import anual, mensual

CANTONES = ('Tulcán', 'Montúfar', 'Bolívar', 'Espejo', 'Mira', 'San Pedro de Huaca')
CENSO_EDUCACION = 'https://www.censoecuador.gob.ec/wp-content/uploads/2024/04/2022_CPV_Educacion.xlsx'
CENSO_SERVICIOS = 'https://www.censoecuador.gob.ec/wp-content/uploads/2023/12/06_2022_CPV_Servicios_basicos_vivienda.xlsx'
CENSO_TIC = 'https://www.censoecuador.gob.ec/wp-content/uploads/2023/12/03_2022_CPV_TIC.xlsx'
CENSO_2010 = 'https://www.ecuadorencifras.gob.ec/wp-content/descargas/Manu-lateral/Resultados-provinciales/carchi.pdf'
ENDI_R2 = 'https://www.ecuadorencifras.gob.ec/documentos/web-inec/ENDI/R2/Tabulados_ENDI_R2.xlsx'
ESI_2025 = ('https://www.ecuadorencifras.gob.ec/documentos/web-inec/Poblacion_y_Demografia/Migracion/2025/'
            'Tabulados_series_historicas_ESI_2025.xlsx')
REEM = 'https://www.ecuadorencifras.gob.ec/directoriodeempresas/'
ESPAC_2025 = 'https://www.ecuadorencifras.gob.ec/documentos/web-inec/Estadisticas_agropecuarias/espac/2025/Tabulados_excel_2025.xlsx'
SIPA = 'https://sipa.agricultura.gob.ec/index.php/sipa-estadisticas/estadisticas-descargas/estadisticas-economicas'
ARCONEL = 'https://arconel.gob.ec/publicaciones-estadistica-del-sector-electrico-2/'
TURISMO_MPCEI = 'https://www.produccion.gob.ec/boletin-de-cifras-sector-turismo/'
RUMICHACA = "ubicacion_pcm='(0.814836,-77.662532)'"


def serie(pares, territorio='Carchi', provisional=(), nota=''):
    """Valores anuales a partir de pares (año, valor); `provisional` dice qué años lo son."""
    return [anual(anio, valor, territorio, anio in provisional, nota) for anio, valor in pares]


def cantones(anio, valores, nota=''):
    return [anual(anio, valor, canton, False, nota) for canton, valor in zip(CANTONES, valores)]


def meses(anio_mes_valor, territorio):
    return [mensual(anio, mes, valor, territorio) for anio, mes, valor in anio_mes_valor]


def _mensuales(desde_anio, valores):
    """Una serie mensual continua desde enero de `desde_anio`."""
    salida = []
    for indice, valor in enumerate(valores):
        salida.append((desde_anio + indice // 12, indice % 12 + 1, valor))
    return salida


LECHE_TULCAN = _mensuales(2024, ['0.460', '0.455', '0.445', '0.445', '0.440', '0.450', '0.450', '0.445', '0.430',
                                 '0.430', '0.430', '0.430', '0.455', '0.475', '0.490', '0.490', '0.490', '0.500',
                                 '0.520', '0.520', '0.510', '0.485', '0.500', '0.500', '0.480', '0.495', '0.500',
                                 '0.500', '0.500', '0.525', '0.530'])
LECHE_MONTUFAR = _mensuales(2024, ['0.465', '0.460', '0.450', '0.4533', '0.445', '0.455', '0.450', '0.4567', '0.430',
                                   '0.4267', '0.425', '0.425', '0.4525', '0.4725', '0.485', '0.490', '0.490', '0.490',
                                   '0.510', '0.5125', '0.510', '0.490', '0.510', '0.510', '0.485', '0.500', '0.505',
                                   '0.505', '0.510', '0.520', '0.525'])
PAPA_SAN_GABRIEL = _mensuales(2024, ['29.25', '20.83', '18.37', '17.92', '22.33', '23.71', '30.88', '28.62', '29.92',
                                     '29.39', '28.92', '28.08', '19.75', '16.04', '11.75', '8.12', '8.43', '9.66',
                                     '14.50', '16.37', '23.13', '22.30', '24.50', '16.33', '19.79', '17.29', '15.50',
                                     '18.11', '21.79', '24.11', '27.50'])
PAPA_QUITO = _mensuales(2024, ['28.93', '22.14', '21.66', '21.63', '24.81', '26.08', '30.59', '30.33', '29.96', '30.46',
                               '29.71', '30.54', '21.87', '16.58', '12.24', '10.87', '10.38', '11.46', '17.50', '18.70',
                               '27.89', '26.25', '25.86', '20.19', '23.17', '20.19', '19.37', '19.81', '23.13', '25.38',
                               '28.18'])
PAPA_PRODUCTOR = [(2024, 1, '26.58'), (2024, 4, '18.56'), (2024, 7, '29.94'), (2024, 10, '28.97')] + _mensuales(2025, [
    '18.18', '15.95', '11.07', '7.95', '8.37', '10.58', '15.59', '16.53', '22.00', '21.97', '24.58', '17.03', '20.40',
    '18.82', '14.90', '18.24', '21.39', '22.83', '26.58'])


# ---------------------------------------------------------------- catálogo de fuentes
FUENTES = {
    'inec-enemdu': {'nombre': 'INEC · Encuesta de Empleo, Desempleo y Subempleo (ENEMDU)', 'institucion': 'INEC',
                    'url': 'https://www.ecuadorencifras.gob.ec/empleo-desempleo-y-subempleo/', 'metodo': 'descarga',
                    'acceso': 'abierto', 'periodicidad': 'Anual (representativa por provincia)',
                    'descripcion': 'Tabulados y microdatos anonimizados; los microdatos sensibles exigen declaración de confidencialidad.'},
    'inec-censo': {'nombre': 'INEC · Censo de Población y Vivienda 2022', 'institucion': 'INEC',
                   'url': 'https://www.censoecuador.gob.ec/resultados-censo/', 'metodo': 'descarga', 'acceso': 'abierto',
                   'periodicidad': 'Cada 10 a 12 años', 'descripcion': 'Tabulados por provincia, cantón y parroquia.'},
    'inec-esi': {'nombre': 'INEC · Registro de Entradas y Salidas Internacionales (ESI)', 'institucion': 'INEC',
                 'url': 'https://www.ecuadorencifras.gob.ec/entradas-y-salidas-internacionales/', 'metodo': 'descarga',
                 'acceso': 'abierto', 'periodicidad': 'Anual, con detalle mensual',
                 'descripcion': 'Movimientos migratorios por unidad de control (CENAF Rumichaca) con datos del Ministerio del Interior.'},
    'inec-reem': {'nombre': 'INEC · Registro Estadístico de Empresas (REEM)', 'institucion': 'INEC', 'url': REEM,
                  'metodo': 'descarga', 'acceso': 'abierto', 'periodicidad': 'Anual',
                  'descripcion': 'Empresas, ventas y empleo registrado por provincia y cantón; base de datos abiertos en CSV.'},
    'inec-reess': {'nombre': 'INEC · Registro de Empleo en la Seguridad Social (REESS)', 'institucion': 'INEC',
                   'url': 'https://www.ecuadorencifras.gob.ec/registro-empleo-seguridad-social/', 'metodo': 'descarga',
                   'acceso': 'abierto', 'periodicidad': 'Mensual',
                   'descripcion': 'Empleo registrado en el IESS por provincia; los registros individuales de afiliados no se publican.'},
    'inec-endi': {'nombre': 'INEC · Encuesta Nacional sobre Desnutrición Infantil (ENDI)', 'institucion': 'INEC',
                  'url': 'https://www.ecuadorencifras.gob.ec/encuesta-nacional-desnutricion-infantil/', 'metodo': 'descarga',
                  'acceso': 'abierto', 'periodicidad': 'Anual por ronda',
                  'descripcion': 'Desnutrición, anemia, vacunación y agua segura por provincia, con estimaciones cantonales.'},
    'inec-vitales': {'nombre': 'INEC · Estadísticas vitales (defunciones y nacimientos)', 'institucion': 'INEC',
                     'url': 'https://www.ecuadorencifras.gob.ec/nacimientos-y-defunciones/', 'metodo': 'descarga',
                     'acceso': 'abierto', 'periodicidad': 'Anual'},
    'inec-salud': {'nombre': 'INEC · Camas y Egresos Hospitalarios', 'institucion': 'INEC',
                   'url': 'https://www.ecuadorencifras.gob.ec/camas-y-egresos-hospitalarios/', 'metodo': 'descarga',
                   'acceso': 'abierto', 'periodicidad': 'Anual'},
    'inec-espac': {'nombre': 'INEC · Encuesta de Superficie y Producción Agropecuaria (ESPAC)', 'institucion': 'INEC',
                   'url': 'https://www.ecuadorencifras.gob.ec/estadisticas-agropecuarias-2/', 'metodo': 'descarga',
                   'acceso': 'abierto', 'periodicidad': 'Anual',
                   'descripcion': 'Superficie, producción, ganado y leche por provincia; no publica datos por cantón.'},
    'sri': {'nombre': 'SRI · Estadísticas de recaudación y catastro RUC', 'institucion': 'Servicio de Rentas Internas',
            'url': 'https://www.sri.gob.ec/estadisticas-generales-de-recaudacion-sri', 'metodo': 'descarga',
            'acceso': 'abierto', 'periodicidad': 'Mensual',
            'descripcion': 'Recaudación por provincia y cantón. El catastro RUC trae nombres de personas naturales: solo se publican agregados.'},
    'supercias': {'nombre': 'Superintendencia de Compañías · Directorio de compañías', 'institucion': 'SCVS',
                  'url': 'https://mercadodevalores.supercias.gob.ec/reportes/directorioCompanias.jsf', 'metodo': 'descarga',
                  'acceso': 'abierto', 'periodicidad': 'Diaria (foto del día)'},
    'gad-transparencia': {'nombre': 'GAD del Carchi y de Tulcán · Transparencia y rendición de cuentas',
                          'institucion': 'Gobierno Provincial del Carchi y GAD Municipal de Tulcán',
                          'url': 'https://datosabiertos.carchi.gob.ec/', 'metodo': 'descarga', 'acceso': 'abierto',
                          'licencia': 'CC BY 4.0 (portal del Gobierno Provincial)', 'periodicidad': 'Mensual y anual'},
    'senae': {'nombre': 'SENAE · Estadísticas de comercio exterior por distrito', 'institucion': 'Servicio Nacional de Aduana',
              'url': 'https://www.gob.ec/senae/tramites/atencion-consultas-informacion-estadistica-comercio-exterior',
              'metodo': 'solicitud', 'acceso': 'solicitud', 'periodicidad': 'A pedido',
              'descripcion': 'El detalle por distrito (Tulcán) se pide con un oficio; el trámite prevé una liquidación de pago «en el caso que aplique».'},
    'trm': {'nombre': 'datos.gov.co · Tasa Representativa del Mercado (TRM)', 'institucion': 'Superintendencia Financiera de Colombia',
            'url': 'https://www.datos.gov.co/Econom-a-y-Finanzas/Tasa-de-Cambio-Representativa-del-Mercado-Historic/32sa-8pi3',
            'documentacion': 'https://dev.socrata.com/foundry/www.datos.gov.co/32sa-8pi3', 'metodo': 'api',
            'acceso': 'abierto', 'licencia': 'CC BY-SA 4.0', 'periodicidad': 'Diaria'},
    'migracion-colombia': {'nombre': 'datos.gov.co · Flujos migratorios de Migración Colombia',
                           'institucion': 'Unidad Administrativa Especial Migración Colombia',
                           'url': 'https://www.datos.gov.co/resource/96sh-4v8d.json',
                           'documentacion': 'https://dev.socrata.com/foundry/www.datos.gov.co/96sh-4v8d', 'metodo': 'api',
                           'acceso': 'abierto', 'licencia': 'CC BY-SA 4.0', 'periodicidad': 'Semestral',
                           'descripcion': 'Entradas de extranjeros y salidas de colombianos por puesto de control; Rumichaca se identifica por sus coordenadas.'},
    'agro-narino': {'nombre': 'datos.gov.co · Comercio exterior agropecuario por departamento',
                    'institucion': 'Ministerio de Agricultura de Colombia (DIAN-DANE)',
                    'url': 'https://www.datos.gov.co/resource/rfip-pkv5.json',
                    'documentacion': 'https://dev.socrata.com/foundry/www.datos.gov.co/rfip-pkv5', 'metodo': 'api',
                    'acceso': 'abierto', 'licencia': 'CC BY-SA 4.0', 'periodicidad': 'Trimestral'},
    'mpcei-turismo': {'nombre': 'MPCEI · Boletín de cifras del sector turismo (catastro)',
                      'institucion': 'Ministerio de Producción, Comercio Exterior e Inversiones', 'url': TURISMO_MPCEI,
                      'metodo': 'pagina', 'acceso': 'abierto', 'periodicidad': 'Mensual',
                      'descripcion': 'Alojamiento y establecimientos por provincia; el catastro nominal se pide por solicitud.'},
    'sipa': {'nombre': 'MAG · Sistema de Información Pública Agropecuaria (SIPA)', 'institucion': 'Ministerio de Agricultura',
             'url': SIPA, 'metodo': 'descarga', 'acceso': 'abierto', 'periodicidad': 'Mensual, con un mes de rezago',
             'descripcion': 'Precios al productor, en mercados e industrias lácteas, en archivos XLSX de URL fija.'},
    'mag-leche': {'nombre': 'MAG · Precio mínimo de sustentación de la leche', 'institucion': 'Ministerio de Agricultura',
                  'url': 'https://www.agricultura.gob.ec/aplicacion-del-precio-diferenciado-de-leche/', 'metodo': 'pagina',
                  'acceso': 'abierto', 'periodicidad': 'Anual'},
    'firms': {'nombre': 'NASA FIRMS · Focos de calor por satélite (VIIRS)', 'institucion': 'NASA, LANCE/FIRMS',
              'url': 'https://firms.modaps.eosdis.nasa.gov/active_fire/', 'metodo': 'api', 'acceso': 'abierto',
              'documentacion': 'https://www.earthdata.nasa.gov/data/tools/firms',
              'licencia': 'Datos abiertos de la NASA, con cita de LANCE/FIRMS', 'periodicidad': 'Casi en tiempo real',
              'descripcion': 'Archivo regional de los últimos 7 días, sin clave; la plataforma se queda con los puntos que '
                             'caen dentro de los cantones del Carchi.'},
    'gfw': {'nombre': 'Global Forest Watch · Pérdida de cobertura arbórea', 'institucion': 'World Resources Institute (WRI)',
            'url': 'https://globalnaturewatch.org/dashboards/country/ECU/4/',
            'documentacion': 'https://data-api.globalforestwatch.org/', 'metodo': 'api', 'acceso': 'abierto',
            'licencia': 'CC BY 4.0 (Hansen et al., 2013)', 'periodicidad': 'Anual'},
    'sngr': {'nombre': 'Secretaría de Gestión de Riesgos · Informes de situación de incendios',
             'institucion': 'Secretaría Nacional de Gestión de Riesgos',
             'url': 'https://www.gestionderiesgos.gob.ec/informes-de-situacion-actual-por-eventos-adversos-ecuador/',
             'metodo': 'pagina', 'acceso': 'abierto', 'periodicidad': 'Por evento, con cierre anual'},
    'maate': {'nombre': 'MAATE · Plan de Acción Nacional de Páramos y áreas protegidas',
              'institucion': 'Ministerio del Ambiente, Agua y Transición Ecológica',
              'url': 'https://www.ambienteyenergia.gob.ec/', 'metodo': 'pagina', 'acceso': 'abierto',
              'periodicidad': 'Multianual'},
    'arconel': {'nombre': 'ARCONEL · Estadística del sector eléctrico', 'institucion': 'Agencia de Regulación y Control de Electricidad',
                'url': ARCONEL, 'metodo': 'pagina', 'acceso': 'abierto', 'periodicidad': 'Anual',
                'descripcion': 'PDF anual y Power BI público; su sistema de datos SISDAT exige registro.'},
    'oeco': {'nombre': 'OECO · Boletines de homicidios intencionales (datos del Ministerio del Interior)',
             'institucion': 'Observatorio Ecuatoriano de Crimen Organizado', 'url': 'https://oeco.padf.org/',
             'metodo': 'pagina', 'acceso': 'abierto', 'periodicidad': 'Anual'},
    'inamhi': {'nombre': 'INAMHI · Estaciones meteorológicas de El Ángel, San Gabriel y El Carmelo',
               'institucion': 'Instituto Nacional de Meteorología e Hidrología', 'url': 'https://inamhi.gob.ec/info/',
               'metodo': 'solicitud', 'acceso': 'convenio', 'periodicidad': 'Horaria',
               'descripcion': 'Las series se piden por oficio o convenio; los reanálisis globales suavizan las mínimas y no sirven para contar heladas.'},
    'upec-laboratorios': {'nombre': 'UPEC · Laboratorios de la Universidad', 'institucion': 'Universidad Politécnica Estatal del Carchi',
                          'metodo': 'propia', 'acceso': 'abierto', 'periodicidad': 'Por análisis',
                          'descripcion': 'Análisis de calidad de leche y agua; se publican agregados, sin identificar fincas ni plantas.'},
    'odetur-encuesta': {'nombre': 'ODETUR · Encuesta de perfil del turista', 'institucion': 'Universidad Politécnica Estatal del Carchi',
                        'metodo': 'propia', 'acceso': 'abierto', 'periodicidad': 'Semestral',
                        'descripcion': 'Con consentimiento informado; los microdatos se anonimizan antes de publicarse.'},
}

# Qué fuente del catálogo alimenta cada indicador ya existente.
FUENTE_DE = {
    'desempleo': 'inec-enemdu', 'empleo-adecuado': 'inec-enemdu', 'subempleo': 'inec-enemdu',
    'pobreza-ingresos': 'inec-enemdu', 'pobreza-multidimensional': 'inec-enemdu', 'gini': 'inec-enemdu',
    'pobreza-nbi': 'inec-censo', 'poblacion': 'inec-censo', 'agua-potable': 'inec-censo',
    'extranjeros-residentes': 'inec-censo', 'recaudacion-sri': 'sri', 'importaciones-tulcan': 'senae',
    'tipo-cambio-cop': 'trm', 'entradas-extranjeros-tulcan': 'inec-esi', 'movimientos-tulcan': 'inec-esi',
    'encuestas-acumuladas': 'odetur-encuesta', 'gasto-visitante': 'odetur-encuesta',
    'papa-participacion': 'inec-espac', 'papa-superficie': 'inec-espac', 'leche-produccion': 'inec-espac',
    'precio-papa': 'sipa', 'precio-leche-productor': 'sipa', 'calidad-leche': 'upec-laboratorios',
    'areas-conservacion': 'maate', 'agua-ecoli': 'inec-endi', 'desnutricion-cronica': 'inec-endi',
    'anemia-infantil': 'inec-endi', 'precipitacion': 'inamhi', 'heladas': 'inamhi', 'homicidios': 'oeco',
}

# ---------------------------------------------------------------- ajustes a indicadores existentes
AJUSTES = {
    'tipo-cambio-cop': {
        'fuente': 'Superintendencia Financiera de Colombia, TRM (datos.gov.co)',
        'url_fuente': FUENTES['trm']['url'],
        'limitaciones': 'Promedio mensual de la TRM diaria; el mes en curso es provisional. Un dólar fuerte encarece '
                        'Tulcán frente a Ipiales: un estudio de la UPEC atribuye al tipo de cambio el 76 % de los 1 558 '
                        'locales cerrados en Tulcán en cuatro años.',
    },
    'recaudacion-sri': {
        'fuente': 'SRI, Estadísticas generales de recaudación por provincia y cantón',
        'url_fuente': FUENTES['sri']['url'], 'tipo_fuente': 'registro',
        'limitaciones': 'La recaudación se asigna al domicilio fiscal del RUC, no al lugar donde se genera la actividad.',
        'valores': serie([(2021, '22.006'), (2022, '25.529'), (2023, '27.196'), (2024, '28.067'), (2025, '28.138')],
                         provisional=(2025,), nota='Cifras exactas del archivo del SRI; 2025 «sujeto a revisión»')
        + [anual(anio, valor, canton) for canton, valores in (
            ('Tulcán', ('16.945', '19.474', '19.970', '21.353', '20.402')),
            ('Montúfar', ('2.336', '2.614', '3.002', '2.542', '3.169')),
            ('Espejo', ('1.013', '1.374', '1.915', '1.422', '1.609')),
            ('Bolívar', ('0.740', '0.932', '1.037', '1.137', '1.424')),
            ('Mira', ('0.635', '0.770', '0.808', '1.064', '1.055')),
            ('San Pedro de Huaca', ('0.337', '0.365', '0.465', '0.548', '0.478')),
        ) for anio, valor in zip(range(2021, 2026), valores)],
    },
    'entradas-extranjeros-tulcan': {
        'nombre': 'Entradas de extranjeros por el cantón Tulcán (Rumichaca y Tufiño)',
        'definicion': 'Movimientos de entrada al Ecuador de personas extranjeras por las unidades de control migratorio '
                      'del cantón Tulcán (CENAF Rumichaca y UCM Tufiño), vía terrestre.',
        'url_fuente': ESI_2025,
        'valores': serie([(2022, '118148'), (2023, '188923'), (2024, '104134'), (2025, '107549')],
                         'Punto de control Tulcán', provisional=(2024, 2025), nota='INEC, ESI, hoja 1.1.9'),
    },
    'precio-papa': {
        'nombre': 'Precio mayorista de la papa superchola',
        'definicion': 'Precio promedio mensual del quintal de 100 libras de papa súper chola en el mercado intermedio de '
                      'San Gabriel (Montúfar) y, como referencia nacional, en el Mercado Mayorista de Quito.',
        'unidad_medida': 'USD por quintal', 'fuente': 'MAG, SIPA, precios de mercados mayoristas e intermedios',
        'url_fuente': SIPA, 'territorio_principal': 'San Gabriel', 'desagregacion': 'Mercado',
        'valores': meses(PAPA_SAN_GABRIEL, 'San Gabriel') + meses(PAPA_QUITO, 'Quito'),
    },
    'precio-leche-productor': {
        'definicion': 'Precio promedio mensual por litro de leche cruda que reportan las industrias lácteas (tipo '
                      '«compra») en Tulcán y Montúfar.',
        'fuente': 'MAG, SIPA, precios mensuales de industrias lácteas', 'url_fuente': SIPA, 'tipo_fuente': 'registro',
        'territorio_principal': 'Tulcán', 'desagregacion': 'Cantón',
        'umbral_bajo': '0.5223',
        'mensaje_alerta': 'Bajo el precio mínimo de sustentación vigente (USD 0,5223 por litro desde el 1 de agosto de 2026).',
        'limitaciones': 'La fuente no dice si el precio reportado incluye bonificaciones o descuentos por calidad.',
        'valores': meses(LECHE_TULCAN, 'Tulcán') + meses(LECHE_MONTUFAR, 'Montúfar'),
    },
    'leche-produccion': {
        'fuente': 'INEC, ESPAC', 'url_fuente': ESPAC_2025,
        'limitaciones': 'La ESPAC pregunta por la producción del «día de ayer»: la unidad son litros por día.',
        'valores': serie([(2023, '285073.56'), (2024, '326712.25'), (2025, '339018.40')], nota='ESPAC, producción total'),
    },
    'papa-participacion': {
        'valores': [anual(2025, '46.8', nota='Calculado: producción del Carchi (solo y asociado) sobre la nacional, ESPAC 2025')],
    },
    'papa-superficie': {
        'valores': [anual(2024, '33.1', nota='Calculado: 4 523,73 ha de 13 688,64 ha, ESPAC 2024'),
                    anual(2025, '25.0', nota='Calculado: 3 989,39 ha de 15 979,15 ha, ESPAC 2025')],
    },
    'agua-potable': {
        'nombre': 'Viviendas con agua por red pública', 'url_fuente': CENSO_SERVICIOS,
        'definicion': 'Viviendas particulares ocupadas cuya agua viene de la red pública (municipio, empresa pública, junta '
                      'de agua o GAD parroquial), sobre el total de viviendas.',
        'desagregacion': 'Provincia y cantón',
        'valores': [anual(2010, '86.06', nota='Censo 2010')] + cantones(2022, ('93.52', '97.91', '96.88', '94.11', '81.22', '98.53'))
        + cantones(2010, ('92.24', '87.08', '71.75', '80.84', '60.91', '93.27')),
    },
    'precipitacion': {
        'fuente': 'INAMHI (estaciones automáticas de El Ángel, San Gabriel y El Carmelo) y estación de la UPEC',
        'limitaciones': 'Pendiente del convenio con el INAMHI para usar sus series. Los modelos climáticos globales '
                        '(reanálisis) dan lluvias muy distintas entre sí en la sierra del Carchi y no se publican como dato.',
    },
    'heladas': {
        'fuente': 'INAMHI (estaciones automáticas de El Ángel, San Gabriel y El Carmelo) y estación de la UPEC',
        'limitaciones': 'Pendiente del convenio con el INAMHI. Los reanálisis globales suavizan las temperaturas mínimas '
                        'de la sierra (en 2025 no marcan ninguna helada en Tulcán) y no sirven para contarlas.',
    },
    'anemia-infantil': {
        'fuente': 'INEC, ENDI, tabulados de las rondas 1 y 2', 'url_fuente': ENDI_R2,
        'desagregacion': 'Provincia', 'umbral_alto': '40',
        'mensaje_alerta': 'Anemia «grave» como problema de salud pública según la OMS (40 % o más).',
        'limitaciones': 'Hemoglobina y umbrales ajustados según la directriz OMS 2024; la ronda 1 se recalculó con ese criterio.',
        'valores': [('2022-2023', '2023-01-01', '49.5', 'Carchi', False, 'ENDI ronda 1, recalculada con la directriz OMS 2024'),
                    ('2023-2024', '2024-01-01', '48.7', 'Carchi', False, 'ENDI ronda 2'),
                    ('2022-2023', '2023-01-01', '38.6', 'Ecuador', False, 'Promedio nacional'),
                    ('2023-2024', '2024-01-01', '32.0', 'Ecuador', False, 'Promedio nacional')],
    },
    'desnutricion-cronica': {
        'fuente': 'INEC, ENDI, tabulados de las rondas 1 y 2', 'url_fuente': ENDI_R2,
        'limitaciones': 'Encuesta por muestreo: el valor provincial tiene su intervalo de confianza en la fuente.',
        'valores': [('2022-2023', '2023-01-01', '22.2', 'Carchi', False, 'ENDI ronda 1'),
                    ('2023-2024', '2024-01-01', '22.3', 'Carchi', False, 'ENDI ronda 2'),
                    ('2022-2023', '2023-01-01', '20.1', 'Ecuador', False, 'Promedio nacional'),
                    ('2023-2024', '2024-01-01', '19.3', 'Ecuador', False, 'Promedio nacional')],
    },
    'homicidios': {
        'fuente': 'Ministerio del Interior, procesado por el Observatorio Ecuatoriano de Crimen Organizado (OECO)',
        'url_fuente': 'https://oeco.padf.org/wp-content/uploads/2026/04/Boletin-anual-de-homicidios-2025_VF_Abril.pdf',
        'valores': serie([(2022, '12'), (2023, '13'), (2024, '8'), (2025, '13')], nota='Boletines anuales del OECO'),
    },
}


def _indicador(codigo, nombre, definicion, unidad, fuente, url, valores, linea, fuente_datos, periodicidad='anual',
               sentido='subir', **extra):
    return {'codigo': codigo, 'nombre': nombre, 'definicion': definicion, 'unidad_medida': unidad, 'fuente': fuente,
            'url_fuente': url, 'tipo_fuente': extra.pop('tipo_fuente', 'registro'), 'periodicidad': periodicidad,
            'sentido': sentido, 'valores': valores, 'linea': linea, 'fuente_datos': fuente_datos, **extra}


# ---------------------------------------------------------------- indicadores nuevos
NUEVOS = {
    'observatorio-osezif': [
        _indicador('comercio-agro-narino', 'Compras agropecuarias de Nariño al Ecuador',
                   'Importaciones agropecuarias y agroindustriales de Colombia desde el Ecuador con destino al '
                   'departamento de Nariño, en valor CIF.', 'miles de USD', 'Ministerio de Agricultura de Colombia (DIAN-DANE), datos.gov.co',
                   FUENTES['agro-narino']['url'], [], 'comercio-logistica', 'agro-narino',
                   territorio_principal='Nariño–Ecuador', desagregacion='Año',
                   limitaciones='Solo sector agropecuario; el departamento es el destino de la mercancía, no el paso de frontera. Se actualiza solo.'),
        _indicador('empresas-activas', 'Empresas activas en el Carchi', 'Unidades económicas con domicilio en el Carchi '
                   'que reportaron ventas, empleo registrado o pertenencia al RIMPE en el año.', 'empresas',
                   'INEC, Registro Estadístico de Empresas (REEM)', REEM,
                   serie([(2022, '11326'), (2023, '10616'), (2024, '10447'), (2025, '10572')], provisional=(2025,))
                   + cantones(2025, ('6690', '1701', '543', '745', '550', '343'), 'REEM 2025, provisional')
                   + cantones(2024, ('6629', '1676', '527', '732', '537', '346'), 'REEM 2024'),
                   'empresas', 'inec-reem', desagregacion='Provincia y cantón',
                   limitaciones='Desde 2022 el RIMPE es obligatorio: no se compara con los años anteriores.'),
        _indicador('ventas-empresas', 'Ventas de las empresas del Carchi', 'Ventas totales de las empresas del universo '
                   'REEM con domicilio en el Carchi, en dólares corrientes.', 'millones de USD',
                   'INEC, REEM, base de datos abiertos', REEM,
                   serie([(2021, '493.03'), (2022, '552.83'), (2023, '593.35'), (2024, '675.55')])
                   + cantones(2024, ('498.73', '82.54', '24.11', '24.50', '21.62', '24.05'), 'REEM 2024'),
                   'empresas', 'inec-reem', desagregacion='Provincia y cantón',
                   limitaciones='Las ventas se publican con un año de rezago respecto del conteo de empresas.'),
        _indicador('empleo-registrado', 'Empleo registrado en la seguridad social', 'Personas con empleo registrado en el '
                   'IESS (relación de dependencia) en empleadores del Carchi, a diciembre de cada año.', 'personas',
                   'INEC, Registro de Empleo en la Seguridad Social (REESS)', FUENTES['inec-reess']['url'],
                   serie([(2019, '16451'), (2020, '15033'), (2021, '15448'), (2022, '16420'), (2023, '16527'),
                          (2024, '16975'), (2025, '17674')], provisional=(2025,), nota='Corte de diciembre'),
                   'empresas', 'inec-reess'),
        _indicador('companias-activas', 'Compañías activas en la Superintendencia', 'Compañías con domicilio en el Carchi '
                   'en situación legal «activa» en el directorio de la Superintendencia de Compañías.', 'compañías',
                   'Superintendencia de Compañías, Valores y Seguros', FUENTES['supercias']['url'],
                   [('2026-10', '2026-10-01', '606', 'Carchi', False, 'Directorio al 5 de octubre de 2026')]
                   + [('2026-10', '2026-10-01', valor, canton, False, 'Directorio al 5 de octubre de 2026')
                      for canton, valor in zip(CANTONES, ('375', '85', '42', '47', '36', '21'))],
                   'empresas', 'supercias', periodicidad='trimestral', desagregacion='Provincia y cantón',
                   limitaciones='El directorio es una foto del día: la serie se arma guardando un corte cada trimestre.'),
        _indicador('ejecucion-prefectura', 'Ejecución presupuestaria del Gobierno Provincial', 'Presupuesto de gastos '
                   'devengado al 31 de diciembre sobre el codificado.', '%',
                   'Gobierno Provincial del Carchi, transparencia (numeral 6)', FUENTES['gad-transparencia']['url'],
                   serie([(2024, '51.34'), (2025, '67.80')], 'Gobierno Provincial del Carchi',
                         nota='Calculado: suma de las partidas del CSV publicado (devengado sobre codificado)'),
                   'gestion-publica', 'gad-transparencia', territorio_principal='Gobierno Provincial del Carchi'),
        _indicador('ejecucion-tulcan', 'Ejecución presupuestaria del GAD Municipal de Tulcán', 'Presupuesto de gastos '
                   'devengado o ejecutado al cierre del ejercicio sobre el codificado.', '%',
                   'GAD Municipal de Tulcán, liquidación presupuestaria y rendición de cuentas',
                   'https://www.gmtulcan.gob.ec/', serie([(2023, '82.73'), (2024, '60')], 'GAD Municipal de Tulcán'),
                   'gestion-publica', 'gad-transparencia', territorio_principal='GAD Municipal de Tulcán',
                   limitaciones='2023 viene de la liquidación («devengado») y 2024 del formulario de rendición de cuentas '
                                '(«ejecutado»). El formulario 2025 es preliminar e inconsistente y no se carga.'),
    ],
    'observatorio-turismo': [
        _indicador('salidas-colombianos-rumichaca', 'Colombianos que salen hacia el Ecuador por Rumichaca',
                   'Salidas de ciudadanos colombianos registradas por Migración Colombia en el puesto de control del '
                   'puente de Rumichaca: el mercado emisor principal del Carchi.', 'salidas',
                   'Migración Colombia, datos.gov.co', 'https://www.datos.gov.co/resource/efw5-jiej.json', [],
                   'demanda', 'migracion-colombia', periodicidad='mensual', territorio_principal='Rumichaca',
                   limitaciones='Cuenta movimientos, no personas ni turistas. Se actualiza solo cuando Migración Colombia publica.'),
        _indicador('entradas-turismo-tulcan', 'Entradas de extranjeros por turismo en Tulcán', 'Entradas de extranjeros '
                   'por las unidades de control del cantón Tulcán que declararon «turismo» como motivo de viaje.',
                   'entradas', 'INEC, ESI, cuadro de motivo de viaje', ESI_2025,
                   serie([(2022, '114604'), (2023, '121734'), (2024, '99751'), (2025, '103177')], 'Tulcán',
                         provisional=(2024, 2025)), 'demanda', 'inec-esi', territorio_principal='Tulcán'),
        _indicador('entradas-colombianos-tulcan', 'Entradas de colombianos por Tulcán', 'Entradas al Ecuador de personas '
                   'de nacionalidad colombiana por la unidad de control migratorio de Tulcán.', 'entradas',
                   'INEC, ESI, cuadro por nacionalidad', ESI_2025,
                   serie([(2022, '99600'), (2023, '104443'), (2024, '87250'), (2025, '87554')], 'Tulcán',
                         provisional=(2024, 2025)), 'demanda', 'inec-esi', territorio_principal='Tulcán'),
        _indicador('alojamiento-establecimientos', 'Establecimientos de alojamiento registrados', 'Establecimientos de '
                   'alojamiento inscritos en el catastro de servicios turísticos con domicilio en el Carchi.',
                   'establecimientos', 'MPCEI, Boletín de cifras del sector turismo', TURISMO_MPCEI,
                   meses([(2025, 10, '39'), (2025, 11, '41'), (2026, 1, '40'), (2026, 2, '41'), (2026, 3, '41'),
                          (2026, 5, '40'), (2026, 6, '41')], 'Carchi'),
                   'oferta', 'mpcei-turismo', periodicidad='mensual',
                   limitaciones='El boletín no separa por cantón ni por clase de alojamiento.'),
        _indicador('alojamiento-habitaciones', 'Habitaciones de alojamiento registradas', 'Habitaciones declaradas por los '
                   'establecimientos de alojamiento del catastro en el Carchi.', 'habitaciones',
                   'MPCEI, Boletín de cifras del sector turismo', TURISMO_MPCEI,
                   meses([(2025, 10, '684'), (2025, 11, '694'), (2026, 1, '687'), (2026, 2, '695'), (2026, 3, '696'),
                          (2026, 5, '694'), (2026, 6, '718')], 'Carchi'), 'oferta', 'mpcei-turismo', periodicidad='mensual'),
        _indicador('alojamiento-plazas', 'Plazas de alojamiento registradas', 'Capacidad en plazas de los establecimientos '
                   'de alojamiento del catastro en el Carchi.', 'plazas', 'MPCEI, Boletín de cifras del sector turismo',
                   TURISMO_MPCEI,
                   meses([(2025, 10, '1370'), (2025, 11, '1411'), (2026, 1, '1392'), (2026, 2, '1416'), (2026, 3, '1439'),
                          (2026, 5, '1432'), (2026, 6, '1481')], 'Carchi'), 'oferta', 'mpcei-turismo', periodicidad='mensual'),
        _indicador('establecimientos-turisticos', 'Establecimientos turísticos registrados', 'Total de establecimientos del '
                   'catastro de servicios turísticos en el Carchi: alojamiento, alimentos y bebidas, agencias, transporte.',
                   'establecimientos', 'MPCEI, Boletín de cifras del sector turismo', TURISMO_MPCEI,
                   meses([(2025, 10, '93'), (2025, 11, '98'), (2026, 1, '99'), (2026, 2, '99'), (2026, 3, '100'),
                          (2026, 5, '101'), (2026, 6, '104')], 'Carchi'), 'oferta', 'mpcei-turismo', periodicidad='mensual'),
    ],
    'observatorio-cadena-lactea-carchi': [
        _indicador('papa-produccion', 'Producción de papa del Carchi', 'Toneladas de papa (tubérculo fresco) producidas '
                   'en el año, en cultivo solo.', 't', 'INEC, ESPAC', ESPAC_2025,
                   serie([(2023, '115424.50'), (2024, '134064.17'), (2025, '107170.02')]), 'papa', 'inec-espac'),
        _indicador('precio-papa-productor', 'Precio de la papa superchola al productor', 'Precio promedio mensual que '
                   'recibe el productor del Carchi por un quintal de 100 libras de papa superchola.', 'USD por quintal',
                   'MAG, SIPA, precios al productor', SIPA, meses(PAPA_PRODUCTOR, 'Carchi'), 'precios', 'sipa',
                   periodicidad='mensual'),
        _indicador('precio-sustentacion-leche', 'Precio mínimo de sustentación de la leche', 'Precio mínimo por litro de '
                   'leche cruda en finca que la industria debe pagar al productor (52,4 % del PVP referencial de la '
                   'leche UHT en funda).', 'USD por litro', 'MAG y MPCEI, acuerdos y actualizaciones del PVP referencial',
                   FUENTES['mag-leche']['url'],
                   [anual(2013, '0.42', 'Ecuador', nota='Acuerdo Ministerial 394, vigente hasta 2024'),
                    anual(2024, '0.5028', 'Ecuador', True, 'Citado por la prensa a partir del MAG'),
                    anual(2025, '0.5043', 'Ecuador', True, 'Desde el 1 de junio de 2025, citado por la prensa'),
                    anual(2026, '0.5223', 'Ecuador', nota='Desde el 1 de agosto de 2026, documento oficial del MAG')],
                   'precios', 'mag-leche', territorio_principal='Ecuador', sentido='neutro'),
        _indicador('existencias-bovinos', 'Ganado vacuno del Carchi', 'Cabezas de ganado vacuno en la provincia el día de '
                   'la encuesta; base para la sanidad animal y la producción de leche.', 'cabezas', 'INEC, ESPAC',
                   ESPAC_2025, serie([(2024, '89518.67'), (2025, '101591.73')]), 'leche', 'inec-espac'),
        _indicador('vacas-ordenadas', 'Vacas ordeñadas en el Carchi', 'Vacas ordeñadas el día de referencia de la encuesta.',
                   'cabezas', 'INEC, ESPAC', ESPAC_2025,
                   serie([(2023, '28392.31'), (2024, '35921.43'), (2025, '32553.03')]), 'leche', 'inec-espac'),
    ],
    'observatorio-ambiental-agua-clima': [
        _indicador('superficie-paramo', 'Superficie de páramo del Carchi', 'Superficie cubierta por el ecosistema páramo '
                   'en la provincia según el mapa de cobertura del MAAE (2020).', 'ha', 'MAATE, Plan de Acción Nacional de Páramos',
                   'https://www.ambienteyenergia.gob.ec/ambiente/wp-content/uploads/downloads/2023/11/PLAN-DE-ACCION-NACIONAL-PARA-LA-CONSERVACION-RESTAURACION-Y-USO-SOSTENIBLE-DE-LOS-PARAMOS.pdf',
                   [anual(2020, '48878', nota='El 3,2 % del páramo nacional')], 'paramo', 'maate',
                   periodicidad='quinquenal'),
        _indicador('incendios-forestales', 'Superficie afectada por incendios forestales', 'Hectáreas de cobertura vegetal '
                   'quemadas en el año según los informes de cierre de la Secretaría de Gestión de Riesgos.', 'ha',
                   'Secretaría Nacional de Gestión de Riesgos, informes de situación', FUENTES['sngr']['url'],
                   [anual(2023, '3803.50', provisional=True, nota='Corte al 16 de noviembre de 2023; 97 eventos'),
                    anual(2024, '3282.31', nota='Cierre; 86 eventos'), anual(2025, '325.95', nota='Cierre; 63 eventos')]
                   + cantones(2024, ('29.81', '93.71', '303.21', '2554.51', '301.02', '0.05'))
                   + cantones(2025, ('3.57', '36.14', '140.70', '18.50', '127.04', '0')),
                   'paramo', 'sngr', sentido='bajar', desagregacion='Provincia y cantón'),
        _indicador('perdida-cobertura-arborea', 'Pérdida de cobertura arbórea', 'Hectáreas de cobertura arbórea (densidad '
                   'de copa de 30 % o más) perdidas en el año en el Carchi, según el monitoreo satelital de la Universidad '
                   'de Maryland.', 'ha', 'Global Forest Watch (Hansen et al., 2013)', FUENTES['gfw']['url'], [],
                   'paramo', 'gfw', sentido='bajar',
                   limitaciones='Detección satelital: incluye pérdida por incendios, tala y cambio de uso. Se actualiza sola cada año.'),
        _indicador('focos-calor', 'Focos de calor detectados en el Carchi', 'Focos de calor que el satélite VIIRS '
                   'detecta en el día dentro de los cantones del Carchi: incendios de vegetación, quemas agrícolas u '
                   'otras fuentes de calor intenso.', 'focos', 'NASA FIRMS (VIIRS), recortado con los límites cantonales',
                   FUENTES['firms']['url'], [], 'paramo', 'firms', periodicidad='diaria', sentido='bajar',
                   tipo_fuente='estacion', umbral_alto='2',
                   mensaje_alerta='Más de 2 focos de calor en un día: revisar si hay incendios en el páramo o quemas.',
                   limitaciones='Un foco no siempre es un incendio forestal: también detecta quemas agrícolas. Las nubes '
                                'pueden ocultar focos. Se actualiza solo varias veces al día.'),
        _indicador('cobertura-alcantarillado', 'Viviendas conectadas al alcantarillado', 'Viviendas particulares ocupadas '
                   'con inodoro conectado a la red pública de alcantarillado.', '%', 'INEC, Censo 2022', CENSO_SERVICIOS,
                   [anual(2022, '79.42'), anual(2010, '73.67')]
                   + cantones(2022, ('81.24', '74.49', '76.86', '85.74', '75.06', '79.43'))
                   + cantones(2010, ('80.21', '65.06', '61.41', '76.97', '65.00', '68.21')),
                   'agua', 'inec-censo', periodicidad='quinquenal', desagregacion='Provincia y cantón'),
        _indicador('energia-facturada', 'Energía eléctrica facturada en el Carchi', 'Energía facturada a los consumidores '
                   'regulados de la distribuidora en la provincia.', 'GWh', 'ARCONEL, Estadística del sector eléctrico',
                   ARCONEL, serie([(2014, '77.11'), (2015, '81.26'), (2016, '80.54'), (2017, '81.61'), (2018, '83.51'),
                                   (2019, '85.37'), (2020, '84.62'), (2021, '88.13'), (2022, '87.69'), (2023, '92.62'),
                                   (2024, '90.85'), (2025, '98.71')]), 'energia', 'arconel', sentido='neutro',
                   limitaciones='2024 fue un año con racionamientos por sequía.'),
        _indicador('clientes-electricos', 'Clientes del servicio eléctrico', 'Consumidores regulados de la distribuidora '
                   'en el Carchi al cierre del año.', 'clientes', 'ARCONEL, Estadística del sector eléctrico', ARCONEL,
                   serie([(2023, '62763'), (2024, '63284'), (2025, '64390')]), 'energia', 'arconel'),
        _indicador('cobertura-electrica', 'Viviendas con electricidad de la red pública', 'Viviendas particulares ocupadas '
                   'con energía eléctrica de la red pública.', '%', 'INEC, Censo 2022', CENSO_SERVICIOS,
                   [anual(2022, '97.99'), anual(2010, '97.17')]
                   + cantones(2022, ('97.42', '99.11', '98.28', '98.84', '97.63', '98.70'))
                   + cantones(2010, ('96.39', '98.83', '97.76', '98.18', '96.08', '98.05')),
                   'energia', 'inec-censo', periodicidad='quinquenal', desagregacion='Provincia y cantón'),
        _indicador('potencia-renovable', 'Potencia renovable instalada en el Carchi', 'Potencia nominal de las centrales de '
                   'generación renovable (hidráulicas) ubicadas en la provincia.', 'MW', 'ARCONEL, Estadística del sector eléctrico',
                   ARCONEL, [anual(2023, '5.82', nota='4 centrales'), anual(2024, '6.81', nota='5 centrales hidráulicas')],
                   'energia', 'arconel'),
    ],
    'observatorio-social-frontera': [
        _indicador('entradas-extranjeros-rumichaca-colombia', 'Extranjeros que entran a Colombia por Rumichaca',
                   'Entradas de extranjeros a Colombia registradas por Migración Colombia en el puesto del puente de '
                   'Rumichaca (incluye a ecuatorianos y venezolanos).', 'entradas', 'Migración Colombia, datos.gov.co',
                   FUENTES['migracion-colombia']['url'], [], 'movilidad', 'migracion-colombia', periodicidad='mensual',
                   territorio_principal='Rumichaca', sentido='neutro',
                   limitaciones='Datos agregados por mes y nacionalidad, sin datos personales. Se actualiza solo.'),
        _indicador('desnutricion-menores-5', 'Desnutrición crónica en menores de 5 años', 'Niñas y niños menores de 5 años '
                   'con talla para la edad menor a −2 desviaciones estándar del patrón OMS.', '%', 'INEC, ENDI', ENDI_R2,
                   [('2022-2023', '2023-01-01', '23.0', 'Carchi', False, 'ENDI ronda 1'),
                    ('2023-2024', '2024-01-01', '22.9', 'Carchi', False, 'ENDI ronda 2'),
                    ('2022-2023', '2023-01-01', '17.5', 'Ecuador', False, 'Promedio nacional'),
                    ('2023-2024', '2024-01-01', '17.5', 'Ecuador', False, 'Promedio nacional')]
                   + [('2022-2023', '2023-01-01', valor, canton, True, 'Estimación cantonal del INEC basada en modelos')
                      for canton, valor in zip(CANTONES, ('23.7', '22.4', '16.2', '22.8', '16.7', '27.4'))],
                   'salud', 'inec-endi', periodicidad='eventual', sentido='bajar', umbral_alto='20',
                   mensaje_alerta='Prevalencia «alta» (20 % o más) según la clasificación OMS y UNICEF (de Onis et al., 2019).',
                   desagregacion='Provincia y cantón (estimación en áreas pequeñas)'),
        _indicador('vacunacion-pentavalente', 'Niñez vacunada con pentavalente (tres dosis)', 'Niñas y niños de 12 a 59 '
                   'meses que recibieron las tres dosis de pentavalente antes del año de edad.', '%', 'INEC, ENDI', ENDI_R2,
                   [('2022-2023', '2023-01-01', '97.5', 'Carchi', False, 'ENDI ronda 1'),
                    ('2023-2024', '2024-01-01', '96.1', 'Carchi', False, 'ENDI ronda 2'),
                    ('2022-2023', '2023-01-01', '92.0', 'Ecuador', False, 'Promedio nacional'),
                    ('2023-2024', '2024-01-01', '90.3', 'Ecuador', False, 'Promedio nacional')],
                   'salud', 'inec-endi', periodicidad='eventual', umbral_bajo='95',
                   mensaje_alerta='Bajo la cobertura de 95 % que recomienda la OPS.'),
        _indicador('mortalidad-infantil', 'Tasa de mortalidad infantil', 'Defunciones de menores de 1 año por cada 1 000 '
                   'nacimientos estimados, según la provincia de residencia.', 'por 1 000 nacimientos',
                   'INEC, Registro Estadístico de Defunciones Generales', FUENTES['inec-vitales']['url'],
                   serie([(2019, '11.86'), (2020, '10.08'), (2021, '8.23'), (2022, '9.20'), (2023, '13.96'), (2024, '8.47')],
                         provisional=(2020, 2021, 2024)), 'salud', 'inec-vitales', sentido='bajar',
                   limitaciones='Con 22 a 37 casos al año, la tasa provincial oscila mucho: conviene leer la tendencia.'),
        _indicador('fecundidad-adolescente', 'Fecundidad adolescente (15 a 19 años)', 'Nacidos vivos de madres de 15 a 19 '
                   'años por cada 1 000 mujeres de esa edad.', 'por 1 000 mujeres', 'INEC, Nacidos vivos y defunciones fetales',
                   FUENTES['inec-vitales']['url'],
                   serie([(2023, '31.99'), (2024, '32.0'), (2025, '31.1')], provisional=(2025,))
                   + serie([(2023, '45.19'), (2024, '39.75'), (2025, '37.24')], 'Ecuador', provisional=(2025,)),
                   'salud', 'inec-vitales', sentido='bajar'),
        _indicador('camas-hospitalarias', 'Camas hospitalarias por 10 000 habitantes', 'Camas hospitalarias disponibles por '
                   'cada 10 000 habitantes, según la provincia del establecimiento.', 'por 10 000 habitantes',
                   'INEC, Camas y Egresos Hospitalarios', FUENTES['inec-salud']['url'],
                   [anual(2023, '9.17', nota='175 camas'), anual(2024, '10.57', nota='188 camas')], 'salud', 'inec-salud',
                   limitaciones='La fuente publica por 1 000; aquí se multiplica por 10. Cambió la proyección de población entre años.'),
        _indicador('analfabetismo', 'Tasa de analfabetismo', 'Personas de 15 años o más que no saben leer ni escribir.',
                   '%', 'INEC, Censos 2010 y 2022', CENSO_EDUCACION,
                   [anual(2022, '3.63', nota='Calculado: 4 821 de 132 790'), anual(2010, '6.2'), anual(2001, '7.2')]
                   + cantones(2022, ('3.49', '3.22', '4.02', '3.43', '5.84', '2.68'), 'Calculado con la tabla 6.1')
                   + cantones(2010, ('5.5', '5.8', '7.6', '6.9', '10.1', '5.7')),
                   'educacion', 'inec-censo', periodicidad='quinquenal', sentido='bajar', desagregacion='Provincia y cantón'),
        _indicador('hogares-internet', 'Hogares con internet', 'Hogares que disponen de internet (fijo en 2022) sobre el '
                   'total de hogares.', '%', 'INEC, Censos 2010 y 2022', CENSO_TIC,
                   [anual(2022, '56.86', nota='Calculado: 30 541 de 53 716 hogares'), anual(2010, '5.3')]
                   + cantones(2022, ('60.96', '55.56', '45.85', '57.50', '48.10', '51.71'), 'Calculado con la tabla 3.1')
                   + cantones(2010, ('7.08', '4.04', '2.02', '2.73', '3.70', '4.09')),
                   'educacion', 'inec-censo', periodicidad='quinquenal', desagregacion='Provincia y cantón',
                   limitaciones='En 2022 se pregunta por internet fijo; en 2010, por disponibilidad de internet.'),
        _indicador('personas-internet', 'Personas que usan internet', 'Personas de 5 años o más que usaron internet en el '
                   'periodo de referencia.', '%', 'INEC, Censos 2010 y 2022', CENSO_TIC,
                   [anual(2022, '65.46', nota='Calculado: 105 704 de 161 487'), anual(2010, '22.34', nota='Calculado')]
                   + cantones(2022, ('67.88', '63.04', '60.00', '65.91', '61.79', '62.24'), 'Calculado con la tabla 1.1'),
                   'educacion', 'inec-censo', periodicidad='quinquenal', desagregacion='Provincia y cantón',
                   limitaciones='Cambia el periodo de referencia: 6 meses en 2010 y 3 meses en 2022.'),
        _indicador('tasa-homicidios', 'Tasa de homicidios intencionales', 'Víctimas de homicidio intencional por cada '
                   '100 000 habitantes en el año.', 'por 100 000 habitantes',
                   'Ministerio del Interior, procesado por el OECO', FUENTES['oeco']['url'],
                   serie([(2022, '6.94'), (2023, '7.26'), (2024, '4.50'), (2025, '7.34')])
                   + serie([(2022, '27.58'), (2023, '46.25'), (2024, '39.14'), (2025, '50.9')], 'Ecuador'),
                   'seguridad', 'oeco', sentido='bajar'),
    ],
}

# Los indicadores existentes en cada línea; los nuevos traen la suya.
LINEA_DE = {
    'carga-rumichaca': 'comercio-logistica', 'exportaciones-colombia-rumichaca': 'comercio-logistica',
    'exportaciones-ecuador-rumichaca': 'comercio-logistica', 'importaciones-tulcan': 'comercio-logistica',
    'tipo-cambio-cop': 'comercio-logistica', 'desempleo': 'empleo-pobreza', 'empleo-adecuado': 'empleo-pobreza',
    'subempleo': 'empleo-pobreza', 'pobreza-ingresos': 'empleo-pobreza', 'pobreza-multidimensional': 'empleo-pobreza',
    'gini': 'empleo-pobreza', 'pobreza-nbi': 'empleo-pobreza', 'recaudacion-sri': 'empresas',
    'poblacion': 'gestion-publica', 'entradas-extranjeros-tulcan': 'demanda', 'gasto-visitante': 'demanda',
    'encuestas-acumuladas': 'demanda', 'visitantes-cementerio': 'eventos', 'ocupacion-feriado': 'eventos',
    'papa-participacion': 'papa', 'papa-superficie': 'papa', 'precio-papa': 'precios', 'leche-produccion': 'leche',
    'precio-leche-productor': 'precios', 'calidad-leche': 'leche', 'paramo-quemado': 'paramo',
    'areas-conservacion': 'paramo', 'agua-potable': 'agua', 'agua-ecoli': 'agua', 'precipitacion': 'agua',
    'heladas': 'agua', 'movimientos-tulcan': 'movilidad', 'flujo-irregular': 'movilidad',
    'extranjeros-residentes': 'movilidad', 'desnutricion-cronica': 'salud', 'anemia-infantil': 'salud',
    'homicidios': 'seguridad',
}

# ---------------------------------------------------------------- conexiones automáticas
CONECTORES = {
    'tipo-cambio-cop': ('socrata', 24, {
        'dominio': 'www.datos.gov.co', 'conjunto': '32sa-8pi3', 'campo_fecha': 'vigenciadesde',
        'campo_valor': 'valor::number', 'agregacion': 'avg', 'por': 'mes', 'desde': '2024-01-01',
        'territorio': 'Frontera Carchi–Nariño'}),
    'salidas-colombianos-rumichaca': ('socrata', 168, {
        'dominio': 'www.datos.gov.co', 'conjunto': 'efw5-jiej', 'campo_anio': 'a_o', 'campo_mes': 'mes',
        'campo_valor': 'total::number', 'filtro': RUMICHACA + " AND pa_s_destino='Ecuador'", 'desde_anio': '2024',
        'territorio': 'Rumichaca'}),
    'entradas-extranjeros-rumichaca-colombia': ('socrata', 168, {
        'dominio': 'www.datos.gov.co', 'conjunto': '96sh-4v8d', 'campo_anio': 'a_o', 'campo_mes': 'mes',
        'campo_valor': 'total::number', 'filtro': RUMICHACA, 'desde_anio': '2024', 'territorio': 'Rumichaca'}),
    'comercio-agro-narino': ('socrata', 168, {
        'dominio': 'www.datos.gov.co', 'conjunto': 'rfip-pkv5', 'campo_anio': 'a_o',
        'campo_valor': 'valor_miles_cif_dol_impo::number', 'filtro': "descripci_n_departamento='Nariño' AND pais='Ecuador'",
        'territorio': 'Nariño–Ecuador'}),
    'focos-calor': ('firms', 6, {
        'url': 'https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/'
               'SUOMI_VIIRS_C2_South_America_7d.csv', 'por': 'dia'}),
    'perdida-cobertura-arborea': ('csv', 720, {
        'url': 'https://data-api.globalforestwatch.org/dataset/gadm__tcl__adm1_change/v20260424/download/csv?sql='
               'select%20umd_tree_cover_loss__year,%20sum(umd_tree_cover_loss__ha)%20as%20ha%20from%20data%20where%20'
               "iso='ECU'%20and%20adm1=4%20and%20umd_tree_cover_density_2000__threshold=30%20group%20by%20"
               'umd_tree_cover_loss__year',
        'columna_periodo': 'umd_tree_cover_loss__year', 'columna_valor': 'ha', 'por': 'anio', 'desde_anio': '2015'}),
}

# ---------------------------------------------------------------- visores de otras instituciones
POWERBI = 'https://app.powerbi.com/view?r='
TABLEAU = 'https://public.tableau.com/views/{}?:embed=y&:showVizHome=no'
INEC_VISORES = 'https://www.ecuadorencifras.gob.ec/documentos/web-inec/Sitios/micrositios_visualizadores/'


def visor(titulo, descripcion, plataforma, url, institucion, linea, url_datos=''):
    return {'titulo': titulo, 'descripcion': descripcion, 'plataforma': plataforma, 'url': url,
            'institucion': institucion, 'linea': linea, 'url_datos': url_datos,
            'responsable': f'{institucion} (fuente externa)'}


VISORES_INSTITUCIONALES = {
    'observatorio-osezif': (
        visor('Comercio exterior de Colombia', 'Tablero de la DIAN con el comercio de Colombia por país socio y aduana '
              '(Ipiales).', 'powerbi', POWERBI + 'eyJrIjoiZjk4OWFjMGUtNzhiOC00YjA1LTljODItNmFmYjViNWFjMTc1IiwidCI6ImZhYjI2ZTVhLTczN2EtNDQzOC04Y2NkLThlNDY1ZWNmMjFkOCIsImMiOjR9',
              'DIAN (Colombia)', 'comercio-logistica',
              'https://www.dian.gov.co/dian/cifras/Paginas/Bases-Estadisticas-de-Comercio-Exterior-Importaciones-y-Exportaciones.aspx'),
        visor('Empleo, desempleo y subempleo (ENEMDU)', 'Visualizador del INEC con el mercado laboral por provincia.',
              'powerbi', POWERBI + 'eyJrIjoiNDY3MjljMTYtNGI5Yy00ZWM4LWE4OTYtNjlhYWYxYzcwZTAxIiwidCI6ImYxNThhMmU4LWNhZWMtNDQwNi1iMGFiLWY1ZTI1OWJkYTExMiJ9',
              'INEC', 'empleo-pobreza', 'https://anda.inec.gob.ec/anda5/index.php/catalog'),
        visor('Registro de Empresas (REEM)', 'Empresas, ventas y empleo por provincia y cantón.', 'powerbi',
              POWERBI + 'eyJrIjoiYmVjNTZkYWMtMjBmMC00YzJkLWE1ZTctNjFjMTk3Y2VhZDQ5IiwidCI6ImYxNThhMmU4LWNhZWMtNDQwNi1iMGFiLWY1ZTI1OWJkYTExMiJ9',
              'INEC', 'empresas', REEM),
        visor('Ranking de compañías', 'Ranking de la Superintendencia de Compañías, con filtro por provincia de domicilio.',
              'powerbi', POWERBI + 'eyJrIjoiMDM0NTQzMzUtNjlkYy00MDFhLWI3YzQtYTk5MmYyNDNkYTEwIiwidCI6IjUzYzcyYjU5LWVmNjItNDBlYS1hYjg2LTdlMjcyOTc5MWIwMSJ9',
              'Superintendencia de Compañías', 'empresas'),
    ),
    'observatorio-turismo': (
        visor('Feriados nacionales: ocupación, gasto y viajes', 'Estadísticas de feriados por provincia del Viceministerio '
              'de Turismo.', 'tableau', TABLEAU.format('Estadsticasdeferiadosnacionales-Oferta/A_G_A'),
              'Viceministerio de Turismo (MPCEI)', 'eventos'),
        visor('Catastro turístico', 'Visualizador del catastro: alojamiento, alimentos y bebidas, agencias y turismo '
              'comunitario por territorio.', 'tableau', TABLEAU.format('Catastro_MPCEI/Catastros_visualizador'),
              'Viceministerio de Turismo (MPCEI)', 'oferta'),
        visor('Flujos migratorios de Colombia 2026', 'Entradas y salidas por puesto de control de Migración Colombia.',
              'tableau', TABLEAU.format('FlujosMigratorios-2026/Inicio'), 'Migración Colombia', 'demanda',
              'https://portal.migracioncolombia.gov.co/planeacion-y-estadistica/observatorio-om3/datos-abiertos/microdatos'),
        visor('Turismo en Nariño e Ipiales', 'Estadísticas territoriales de turismo del MinCIT por departamento y municipio.',
              'powerbi', POWERBI + 'eyJrIjoiYzZjZDAzMmYtMzM1Yi00NzlmLTlkYTAtYmU5MGM3YmFhYjI2IiwidCI6IjQxMTNjNDQ2LTZjYWItNGEwMC1iOTYzLTgzNWQ1MGI2MWEyZiJ9&pageName=ReportSection',
              'MinCIT (Colombia)', 'demanda'),
    ),
    'observatorio-cadena-lactea-carchi': (
        visor('Estadísticas agropecuarias (ESPAC)', 'Superficie, producción y ganado por provincia.', 'powerbi',
              POWERBI + 'eyJrIjoiYzEzMTkyYjctNmEwNi00ZmQ5LTk0NTItNmY2OTk4MjkwMzE5IiwidCI6ImYxNThhMmU4LWNhZWMtNDQwNi1iMGFiLWY1ZTI1OWJkYTExMiJ9',
              'INEC', 'papa', 'https://anda.inec.gob.ec/anda5/index.php/catalog'),
    ),
    'observatorio-ambiental-agua-clima': (
        visor('Pérdida de cobertura arbórea en el Carchi', 'Serie anual de pérdida de bosque en la provincia.', 'otra',
              'https://globalnaturewatch.org/embed/widget/treeLoss/country/ECU/4/', 'Global Forest Watch (WRI)', 'paramo',
              'https://data-api.globalforestwatch.org/'),
        visor('Alertas de incendio en el Carchi', 'Alertas históricas de incendio detectadas por satélite (VIIRS).', 'otra',
              'https://globalnaturewatch.org/embed/widget/firesAlertsHistorical/country/ECU/4/', 'Global Forest Watch (WRI)',
              'paramo', 'https://firms.modaps.eosdis.nasa.gov/download/'),
        visor('Pérdidas de energía eléctrica', 'Indicadores de pérdidas por empresa distribuidora (en el Carchi, EMELNORTE).',
              'powerbi', POWERBI + 'eyJrIjoiNjI1MDQ3NDMtNjc2ZC00Y2QzLWFjMjQtZDdkNDVjYzM4YzgzIiwidCI6IjY4MmE0ZTZhLWE3N2YtNDk1OC1hM2FjLTllMjY2ZDE4YWEzNyIsImMiOjR9',
              'ARCONEL', 'energia', ARCONEL),
    ),
    'observatorio-social-frontera': (
        visor('Monitoreo de protección 2025', 'Estadísticas del monitoreo de protección del ACNUR en el Ecuador.', 'powerbi',
              POWERBI + 'eyJrIjoiMDRjYWZhZjUtZGY1OC00MzBlLWE0MzktNDVmM2Y3MjlhYjZkIiwidCI6ImU1YzM3OTgxLTY2NjQtNDEzNC04YTBjLTY1NDNkMmFmODBiZSIsImMiOjh9',
              'ACNUR Ecuador', 'movilidad', 'https://data.unhcr.org/en/country/ecu'),
        visor('Migración irregular en tránsito', 'Corredor de tránsito por la frontera colombo-ecuatoriana.', 'tableau',
              TABLEAU.format('MigracionIrregularenTransito/Migracinirregularentrnsito'), 'Migración Colombia', 'movilidad'),
        visor('Desnutrición infantil (ENDI)', 'Visualizador de la ENDI por provincia.', 'powerbi',
              POWERBI + 'eyJrIjoiYmFmYmU2ZDUtNDFlNS00NGNjLWJjOGUtM2YwZjRjMzIzNzVlIiwidCI6ImYxNThhMmU4LWNhZWMtNDQwNi1iMGFiLWY1ZTI1OWJkYTExMiJ9',
              'INEC', 'salud', 'https://anda.inec.gob.ec/anda5/index.php/catalog'),
        visor('Censo Ecuador 2022', 'Población, vivienda, educación y migración por provincia y cantón.', 'powerbi',
              POWERBI + 'eyJrIjoiNWUzMjQwOWMtZjFhOS00NjczLTk0YTItNjcwZmRmY2YxMjkyIiwidCI6ImYxNThhMmU4LWNhZWMtNDQwNi1iMGFiLWY1ZTI1OWJkYTExMiJ9',
              'INEC', 'educacion', 'https://www.censoecuador.gob.ec/resultados-censo/'),
        visor('Defunciones generales', 'Defunciones por provincia y causa, incluidas las muertes por agresión.', 'powerbi',
              POWERBI + 'eyJrIjoiNTM0YjE3YTQtODc3OS00YTc2LTk0YjAtNmQ3ZTQzYmVlNWJkIiwidCI6ImYxNThhMmU4LWNhZWMtNDQwNi1iMGFiLWY1ZTI1OWJkYTExMiJ9',
              'INEC', 'seguridad', 'https://anda.inec.gob.ec/anda5/index.php/catalog'),
    ),
}


# ---------------------------------------------------------------- tableros por eje y vista
# (título, qué permite ver, línea, vista, indicadores). Un tablero solo reúne indicadores con datos publicados.
TABLEROS = {
    'observatorio-osezif': (
        ('Comercio y logística por Rumichaca', 'Carga, exportaciones en ambos sentidos, importaciones, compras '
         'agropecuarias de Nariño y tipo de cambio.', 'comercio-logistica', 'series',
         ('carga-rumichaca', 'exportaciones-colombia-rumichaca', 'exportaciones-ecuador-rumichaca', 'importaciones-tulcan',
          'tipo-cambio-cop', 'comercio-agro-narino')),
        ('Empleo y pobreza', 'Mercado laboral, pobreza por ingresos, multidimensional y por NBI, y desigualdad.',
         'empleo-pobreza', 'series',
         ('desempleo', 'empleo-adecuado', 'subempleo', 'pobreza-ingresos', 'pobreza-multidimensional', 'gini', 'pobreza-nbi')),
        ('Pobreza y población por cantón', 'Dónde se concentra la pobreza por necesidades básicas insatisfechas.',
         'empleo-pobreza', 'mapa', ('pobreza-nbi', 'poblacion')),
        ('Empresas y empleo formal', 'Empresas activas, ventas, empleo registrado, compañías y recaudación.',
         'empresas', 'series', ('empresas-activas', 'ventas-empresas', 'empleo-registrado', 'companias-activas', 'recaudacion-sri')),
        ('Empresas y recaudación por cantón', 'El tejido empresarial y tributario de cada cantón.', 'empresas', 'mapa',
         ('empresas-activas', 'ventas-empresas', 'recaudacion-sri')),
        ('Ejecución presupuestaria de los GAD', 'Cuánto de su presupuesto ejecutan la Prefectura y el GAD de Tulcán.',
         'gestion-publica', 'series', ('ejecucion-prefectura', 'ejecucion-tulcan', 'poblacion')),
    ),
    'observatorio-turismo': (
        ('Visitantes y feriados', 'Entradas por Rumichaca, visitantes colombianos, el 2 de noviembre y la ocupación.',
         'demanda', 'series',
         ('entradas-extranjeros-tulcan', 'entradas-turismo-tulcan', 'entradas-colombianos-tulcan',
          'salidas-colombianos-rumichaca', 'visitantes-cementerio', 'ocupacion-feriado', 'encuestas-acumuladas')),
        ('Capacidad de alojamiento', 'Establecimientos, habitaciones y plazas del catastro turístico.', 'oferta', 'series',
         ('alojamiento-establecimientos', 'alojamiento-habitaciones', 'alojamiento-plazas', 'establecimientos-turisticos')),
    ),
    'observatorio-cadena-lactea-carchi': (
        ('Papa', 'Producción, superficie y peso del Carchi en la papa del país.', 'papa', 'series',
         ('papa-participacion', 'papa-superficie', 'papa-produccion')),
        ('Leche y ganadería', 'Producción de leche, hato ganadero y vacas en ordeño.', 'leche', 'series',
         ('leche-produccion', 'existencias-bovinos', 'vacas-ordenadas')),
        ('Precios agroalimentarios', 'Papa al productor y en el mercado, leche pagada por la industria y precio mínimo.',
         'precios', 'series', ('precio-papa-productor', 'precio-papa', 'precio-leche-productor', 'precio-sustentacion-leche')),
        ('Precio de la papa por mercado', 'San Gabriel frente al Mercado Mayorista de Quito.', 'precios', 'comparacion',
         ('precio-papa',)),
        ('Precio de la leche frente al mínimo', 'El precio que pagan las industrias frente al de sustentación.', 'precios',
         'semaforo', ('precio-leche-productor', 'precio-sustentacion-leche')),
    ),
    'observatorio-ambiental-agua-clima': (
        ('Páramo, bosques e incendios', 'Superficie de páramo, pérdida de bosque, incendios y áreas protegidas.', 'paramo',
         'series', ('focos-calor', 'superficie-paramo', 'perdida-cobertura-arborea', 'incendios-forestales', 'paramo-quemado',
                    'areas-conservacion')),
        ('Incendios por cantón', 'Hectáreas quemadas en cada cantón.', 'paramo', 'mapa', ('incendios-forestales',)),
        ('Agua y saneamiento por cantón', 'Acceso a agua por red pública y a alcantarillado.', 'agua', 'mapa',
         ('agua-potable', 'cobertura-alcantarillado')),
        ('Energía', 'Consumo, clientes, cobertura y potencia renovable instalada.', 'energia', 'series',
         ('energia-facturada', 'clientes-electricos', 'cobertura-electrica', 'potencia-renovable')),
        ('Electricidad por cantón', 'Viviendas con electricidad de la red pública.', 'energia', 'mapa', ('cobertura-electrica',)),
    ),
    'observatorio-social-frontera': (
        ('Movilidad humana', 'Cruces por Rumichaca, flujo irregular y población extranjera residente.', 'movilidad',
         'series', ('movimientos-tulcan', 'flujo-irregular', 'extranjeros-residentes',
                    'entradas-extranjeros-rumichaca-colombia')),
        ('Salud infantil frente a los umbrales', 'Desnutrición, anemia, vacunación y mortalidad con los umbrales de la '
         'OMS, UNICEF y la OPS.', 'salud', 'semaforo',
         ('desnutricion-menores-5', 'desnutricion-cronica', 'anemia-infantil', 'vacunacion-pentavalente',
          'mortalidad-infantil', 'fecundidad-adolescente', 'camas-hospitalarias')),
        ('Desnutrición crónica por cantón', 'Estimación cantonal del INEC en menores de 5 años.', 'salud', 'mapa',
         ('desnutricion-menores-5',)),
        ('Educación y brecha digital por cantón', 'Analfabetismo, hogares con internet y uso de internet.', 'educacion',
         'mapa', ('analfabetismo', 'hogares-internet', 'personas-internet')),
        ('Seguridad', 'Tasa de homicidios del Carchi frente a la del país.', 'seguridad', 'comparacion',
         ('tasa-homicidios',)),
    ),
}

# ---------------------------------------------------------------- levantamientos propios
ENCUESTA_LINEA = {'Perfil del turista Ecuador–Colombia': 'demanda', 'Diagnóstico de productores lecheros': 'leche'}
LEVANTAMIENTOS = {
    'observatorio-osezif': ({
        'nombre': 'Canasta de precios Tulcán–Ipiales', 'linea': 'comercio-logistica', 'etapa': 'diseno',
        'objetivo': 'Comparar cada mes el precio de una canasta de productos de consumo a ambos lados de la frontera '
                    'para medir cuánto conviene comprar en Ipiales y cómo responde al tipo de cambio.',
        'poblacion': 'Establecimientos comerciales de Tulcán e Ipiales',
        'muestra': 'Canasta fija de productos en los mismos establecimientos cada mes', 'periodicidad': 'mensual',
        'proximo_levantamiento': '2027-I'}, {
        'nombre': 'Tiempos de cruce y despacho de carga en Rumichaca', 'linea': 'comercio-logistica', 'etapa': 'diseno',
        'objetivo': 'Medir cuántas horas pasa un camión desde que llega al patio de Rumichaca hasta que sale despachado, '
                    'por sentido y tipo de carga, para saber cuánto cuesta la espera a transportistas y exportadores.',
        'poblacion': 'Camiones de carga que cruzan el puente internacional de Rumichaca',
        'muestra': 'Registro de llegada y salida de camiones en días fijos de cada mes, con los gremios de transporte '
                   'y los agentes de aduana', 'periodicidad': 'mensual',
        'proximo_levantamiento': '2027-I'}),
    'observatorio-ambiental-agua-clima': ({
        'nombre': 'Calidad del agua en sistemas comunitarios', 'linea': 'agua', 'etapa': 'diseno',
        'objetivo': 'Medir la calidad física, química y microbiológica del agua de los sistemas comunitarios rurales, '
                    'desde la captación hasta el grifo, con el laboratorio de suelos y aguas de la UPEC.',
        'poblacion': 'Sistemas comunitarios de agua (juntas administradoras) del Carchi',
        'muestra': 'Muestras en captación, tanque y grifo de cada sistema seleccionado', 'periodicidad': 'semestral',
        'proximo_levantamiento': '2027-I'},),
    'observatorio-social-frontera': ({
        'nombre': 'Encuesta a hogares en movilidad humana', 'linea': 'movilidad', 'etapa': 'diseno',
        'objetivo': 'Conocer las condiciones de vida, el empleo y el acceso a salud y educación de los hogares con '
                    'personas migrantes o refugiadas en Tulcán, con OIM y ACNUR.',
        'poblacion': 'Hogares con al menos una persona migrante o refugiada en el cantón Tulcán',
        'muestra': 'Muestra por conglomerados con organizaciones aliadas', 'periodicidad': 'anual',
        'proximo_levantamiento': '2027'},),
}


# ---------------------------------------------------------------- criterios de alerta por variación
# Cuánto puede empeorar un indicador frente al periodo anterior antes de avisar. Es un criterio del observatorio, no
# una norma externa: lo que es «empeorar» lo decide el sentido deseado del indicador. Los umbrales con norma
# (OMS, OPS, precio mínimo de la leche) están en la ficha de cada indicador.
ALERTAS_VARIACION = {
    'entradas-extranjeros-tulcan': ('15', 'Las entradas de extranjeros cayeron más de 15 % frente al año anterior.'),
    'entradas-colombianos-tulcan': ('15', 'Los visitantes colombianos cayeron más de 15 % frente al año anterior.'),
    'salidas-colombianos-rumichaca': ('25', 'Los colombianos que llegan por Rumichaca cayeron más de 25 % frente al mes anterior.'),
    'alojamiento-plazas': ('5', 'La capacidad de alojamiento registrada bajó más de 5 %.'),
    'establecimientos-turisticos': ('5', 'Los establecimientos turísticos registrados bajaron más de 5 %.'),
    'desempleo': ('15', 'El desempleo subió más de 15 % frente al año anterior.'),
    'pobreza-ingresos': ('10', 'La pobreza por ingresos subió más de 10 % frente al año anterior.'),
    'empresas-activas': ('3', 'Las empresas activas bajaron más de 3 % frente al año anterior.'),
    'empleo-registrado': ('3', 'El empleo registrado en la seguridad social bajó más de 3 %.'),
    'recaudacion-sri': ('5', 'La recaudación tributaria bajó más de 5 % frente al año anterior.'),
    'ventas-empresas': ('5', 'Las ventas de las empresas bajaron más de 5 % frente al año anterior.'),
    'precio-papa-productor': ('20', 'El precio de la papa al productor cayó más de 20 % frente al mes anterior.'),
    'leche-produccion': ('10', 'La producción de leche bajó más de 10 % frente al año anterior.'),
    'existencias-bovinos': ('10', 'El hato ganadero se redujo más de 10 % frente al año anterior.'),
    'incendios-forestales': ('50', 'La superficie quemada creció más de 50 % frente al año anterior.'),
    'perdida-cobertura-arborea': ('50', 'La pérdida de bosque creció más de 50 % frente al año anterior.'),
    'tasa-homicidios': ('25', 'La tasa de homicidios subió más de 25 % frente al año anterior.'),
    'mortalidad-infantil': ('25', 'La mortalidad infantil subió más de 25 % frente al año anterior.'),
}
