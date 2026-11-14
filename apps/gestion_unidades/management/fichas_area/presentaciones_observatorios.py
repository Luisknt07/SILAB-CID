"""Presentación («Conoce la unidad») de los observatorios creados con la reorganización de octubre de 2026.

Los dos están en creación: la Universidad aún no expide su resolución, y así lo dicen su historia y sus hitos.
Se suman al diccionario de presentaciones_unidades.py y los carga el mismo comando.
"""

PRESENTACIONES_OBSERVATORIOS = {
    'observatorio-ambiental-agua-clima': {
        'lema': 'El páramo, el agua y el clima del Carchi medidos para decidir a tiempo',
        'que_es': 'El observatorio de la UPEC que sigue el estado del ambiente del Carchi: la lluvia, la temperatura y '
                  'las heladas, el páramo que da agua a Tulcán y El Ángel, la calidad del agua y la biodiversidad.',
        'que_hace': 'Reúne los datos de la estación meteorológica de la Universidad, del INAMHI y del MAATE, los procesa en '
                    'indicadores con ficha metodológica y publica un boletín agroclimático mensual, con alertas de heladas '
                    'para quienes siembran papa y pastos, y un informe anual del páramo y el agua.',
        'capacidades': 'Cuenta con la estación meteorológica de la UPEC y el Herbario de la Universidad, y con el apoyo del '
                       'Laboratorio de Energías Renovables y Territorio (GNSS, drones y sistemas de información geográfica) y '
                       'del Laboratorio de Análisis y Calidad de Alimentos, Suelos y Aguas para la calidad del agua.',
        'areas_trabajo': 'Clima y heladas; páramo y cobertura vegetal; agua para consumo y riego; biodiversidad; áreas de '
                         'conservación y uso sustentable del Carchi.',
        'historia': 'Se propone en octubre de 2026, al revisar las unidades de la Universidad, porque el Carchi depende del '
                    'páramo para su agua y de la helada para su papa, y ningún observatorio de la UPEC los seguía. Está en '
                    'creación: falta su resolución del Consejo Superior Universitario.',
        'mision': 'Medir de forma continua el clima, el agua y el páramo del Carchi y entregar a tiempo información clara '
                  'para la producción, la gestión del agua y la conservación.',
        'vision': 'Ser la referencia provincial de datos abiertos sobre clima, agua y páramo, usada por productores, juntas '
                  'de agua y gobiernos locales.',
        'objetivos': [
            'Publicar cada mes el boletín agroclimático con lluvia, temperatura y días con helada.',
            'Avisar cuando un indicador cruce su umbral, como las heladas que dañan la papa y los pastos.',
            'Seguir la pérdida de páramo por incendios y avance de la frontera agrícola.',
            'Medir la calidad del agua de consumo con los laboratorios de la Universidad.',
            'Publicar los datos de la estación de la UPEC como datos abiertos.',
        ],
        'beneficiarios': [
            'Productores de papa, leche y pastos del Carchi',
            'Juntas de agua y gobiernos parroquiales y cantonales',
            'Estudiantes y docentes de Agropecuaria, Turismo y Computación',
            'Gobierno Provincial del Carchi y gestores de áreas de conservación',
        ],
        'resultados': [
            'Boletín agroclimático mensual con alertas de heladas',
            'Informe anual del páramo y el agua',
            'Series abiertas de la estación meteorológica de la UPEC',
            'Indicadores de calidad del agua y de áreas de conservación con ficha metodológica',
        ],
        'lineas': [
            ('Clima y heladas', 'fa-cloud-sun-rain', 'Lluvia, temperatura y heladas medidas en la estación de la UPEC.'),
            ('Páramo', 'fa-mountain', 'Cobertura de páramo, incendios y frontera agrícola en El Ángel y las cordilleras.'),
            ('Agua', 'fa-tint', 'Agua para consumo y riego: acceso, calidad y fuentes que nacen en el páramo.'),
            ('Biodiversidad', 'fa-leaf', 'Registros del Herbario de la UPEC y especies del páramo.'),
            ('Alertas', 'fa-bell', 'Avisos cuando un indicador sale del rango esperado.'),
        ],
        'hitos': [
            (2026, 'Propuesta de creación', 'Se propone en la reorganización de unidades de octubre de 2026; espera su resolución.'),
        ],
    },
    'observatorio-social-frontera': {
        'lema': 'Quién cruza la frontera, cómo vive y qué necesita: datos para la salud, la educación y la protección',
        'que_es': 'El observatorio de la UPEC que sigue la movilidad humana por la frontera norte y sus efectos en la salud, '
                  'la nutrición y la educación de la población del Carchi.',
        'que_hace': 'Reúne registros oficiales (INEC, Ministerio del Interior, MSP, Ministerio de Educación) e informes de '
                    'organismos como la OIM y ACNUR, los organiza en indicadores con ficha y publica un boletín semestral y '
                    'notas de política para quienes atienden a la población en movilidad y a la niñez de la provincia.',
        'capacidades': 'Se apoya en las carreras de Enfermería y Laboratorio Clínico, en el Laboratorio de Simulación Clínica '
                       'para la formación de encuestadores en salud, y en el Laboratorio de Inteligencia Artificial y Ciencia '
                       'de Datos para el procesamiento. Los datos de salud se publican solo agregados y anónimos.',
        'areas_trabajo': 'Movilidad humana por Rumichaca y pasos informales; salud y nutrición infantil; acceso a educación; '
                         'seguridad y protección de personas en movilidad.',
        'historia': 'Se propone en octubre de 2026: por el punto de control de Tulcán pasan más de 370 000 movimientos al año y '
                    'por la frontera con Ecuador cruza casi la mitad del flujo irregular de Colombia, mientras la desnutrición '
                    'crónica infantil del Carchi supera el promedio nacional. Está en creación: falta su resolución.',
        'mision': 'Producir información confiable sobre la movilidad humana y las condiciones sociales de la frontera norte '
                  'para orientar la atención en salud, educación y protección.',
        'vision': 'Ser la fuente de referencia de la frontera norte sobre movilidad humana y bienestar, en red con los '
                  'observatorios de Nariño.',
        'objetivos': [
            'Seguir los flujos migratorios por la frontera norte con registros oficiales y de organismos internacionales.',
            'Medir la nutrición infantil y el acceso al agua segura en el Carchi.',
            'Documentar la demanda de salud y educación de la población en movilidad.',
            'Publicar un boletín semestral y notas de política para quienes deciden.',
            'Proteger los datos personales: publicar solo información agregada y anónima.',
        ],
        'beneficiarios': [
            'Personal de salud y educación del Carchi',
            'Organizaciones que atienden a personas en movilidad',
            'Estudiantes y docentes de Enfermería, Laboratorio Clínico, Educación y Administración Pública',
            'Gobiernos locales y juntas de protección de derechos',
        ],
        'resultados': [
            'Boletín semestral de movilidad humana y frontera social',
            'Notas de política sobre nutrición infantil, agua segura y atención a personas en movilidad',
            'Indicadores con ficha metodológica y datos abiertos agregados',
        ],
        'lineas': [
            ('Movilidad humana', 'fa-route', 'Entradas, salidas y flujos irregulares por la frontera norte.'),
            ('Salud y nutrición', 'fa-heartbeat', 'Desnutrición crónica, anemia y salud de la población en movilidad.'),
            ('Educación', 'fa-school', 'Acceso y permanencia de niñas, niños y jóvenes en movilidad.'),
            ('Protección', 'fa-shield-alt', 'Seguridad y protección de las personas en movilidad.'),
        ],
        'hitos': [
            (2026, 'Propuesta de creación', 'Se propone en la reorganización de unidades de octubre de 2026; espera su resolución.'),
        ],
    },
}
