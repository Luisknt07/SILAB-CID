"""Contenido listo para incluir en la planificación y el informe, por tipo de unidad.

Igual que en las guías de práctica: cada apartado ofrece redacciones base que
la unidad inserta con un clic y luego ajusta. Los textos se escriben con los
datos de la unidad (nombre, tipo, facultad, carreras) y salen ya en el HTML
acotado que entiende el editor.
"""

from apps.reservas.presentation.guia_html import texto_a_html

# Redacciones comunes a todo tipo de unidad; `{unidad}`, `{tipo}`, `{facultad}`,
# `{carreras}` y `{periodo}` se reemplazan con los datos reales.
COMUNES = {
    'descripcion': [
        ('Según la ficha pública', '{descripcion_ficha}'),
        ('Presentación institucional',
         '{unidad} es una unidad de la {facultad} al servicio de {carreras}. Brinda espacios, equipamiento y '
         'acompañamiento técnico para la docencia práctica, la investigación y la vinculación con la sociedad, '
         'bajo la normativa institucional de uso, seguridad y registro en la plataforma.'),
    ],
    'mision': [
        ('Misión base',
         'Brindar a estudiantes, docentes e investigadores un espacio seguro y equipado para la práctica, la '
         'experimentación y la generación de conocimiento aplicado, con procesos trazables, personal calificado '
         'y una gestión responsable de los recursos institucionales.'),
    ],
    'vision': [
        ('Visión base',
         'Ser una unidad de referencia regional por la calidad de su práctica formativa, la pertinencia de sus '
         'servicios y su aporte a la solución de problemas del territorio, reconocida por sus procesos '
         'documentados y su mejora continua.'),
    ],
    'politicas': [
        ('Acceso y uso',
         'Toda sesión de uso se solicita y registra en la plataforma institucional antes de ejecutarse.\n'
         'El acceso a la unidad requiere inducción de seguridad vigente y autorización del responsable.\n'
         'Los equipos se operan según su manual y solo con la supervisión que cada uno exige.\n'
         'Los incidentes, daños y no conformidades se reportan el mismo día por el canal institucional.'),
        ('Horario y prioridad',
         'La unidad atiende en el horario publicado en su ficha; fuera de él solo con autorización expresa.\n'
         'Tienen prioridad las prácticas curriculares planificadas; los demás usos se agendan según disponibilidad.'),
    ],
    'estructura': [
        ('Roles y responsabilidades',
         'La unidad depende de la {facultad} y responde ante la Dirección de Investigación.\n'
         '- Coordinación de la unidad: planifica, autoriza usos y responde por el cumplimiento del plan y de la '
         'normativa.\n'
         '- Responsable técnico: opera y mantiene los equipos, controla inventario y seguridad.\n'
         '- Laboratorista o personal de apoyo: atiende reservas, registra la operación diaria y las evidencias.\n'
         '- Docentes usuarios: planifican y ejecutan sus prácticas con guía aprobada y registran su ejecución.'),
    ],
    'objetivo_general': [
        ('Objetivo general base',
         'Garantizar durante el período {periodo} la operación segura, planificada y documentada de {unidad}, '
         'atendiendo las prácticas, proyectos y servicios comprometidos con los recursos disponibles y '
         'registrando sus evidencias en la plataforma.'),
    ],
    'objetivos_especificos': [
        ('Específicos base',
         'Ejecutar el 100 % de las sesiones de uso con registro previo en la plataforma.\n'
         'Cumplir el plan de mantenimiento preventivo de los equipos críticos.\n'
         'Mantener actualizado el inventario de equipos, software y espacios al corte del período.\n'
         'Atender las necesidades de seguridad con inducción a todo usuario nuevo.'),
    ],
    'diagnostico': [
        ('Diagnóstico base',
         'La unidad opera con el equipamiento registrado en el inventario y el personal indicado en su '
         'estructura. Sus principales fortalezas son … Las limitaciones que condicionan la operación del '
         'período son … y se atienden con las necesidades de inversión proyectadas.'),
    ],
    'necesidades': [
        ('Necesidades típicas',
         'Reposición de insumos y consumibles para las prácticas del período.\n'
         'Mantenimiento correctivo de los equipos reportados fuera de servicio.\n'
         'Capacitación del personal en el uso de equipos nuevos o normativa vigente.'),
    ],
    'mobiliario': [
        ('Mobiliario e infraestructura',
         'Mesones de trabajo, sillas y estanterías en estado bueno; instalaciones eléctricas y red de datos '
         'operativas; ventilación e iluminación suficientes para la capacidad declarada. Se detalla lo que '
         'requiera intervención.'),
    ],
    'resumen_ejecutivo': [
        ('Resumen base',
         'Durante el período {periodo}, {unidad} ejecutó las actividades comprometidas en su planificación, '
         'atendió las sesiones registradas en la plataforma y mantuvo la operación de sus equipos y espacios. '
         'Los principales resultados fueron … y las dificultades relevantes …, que se atienden con las acciones '
         'de mejora registradas.'),
    ],
    'analisis_uso': [
        ('Lectura de las cifras',
         'El uso se concentró en … con predominio de usuarios de tipo …; los meses de menor actividad '
         'coinciden con …; la relación entre sesiones registradas y atendidas refleja …'),
    ],
    'logros': [
        ('Logros típicos',
         'Prácticas planificadas ejecutadas con guía aprobada y evidencias registradas.\n'
         'Plan de mantenimiento cumplido en los equipos críticos.\n'
         'Inventario actualizado al corte del período.'),
    ],
    'dificultades': [
        ('Dificultades típicas',
         'Equipos fuera de servicio por falta de repuestos.\n'
         'Insumos insuficientes para el número de estudiantes atendidos.\n'
         'Sesiones sin registro previo en la plataforma.'),
    ],
    'necesidades_siguiente': [
        ('Para el siguiente período',
         'Adquisición o reposición de … según la proyección de inversión.\n'
         'Mantenimiento correctivo de …\n'
         'Capacitación en …'),
    ],
}

# Redacciones propias de cada tipo; se suman a las comunes.
POR_TIPO = {
    'laboratorios': {
        'mision': [('Laboratorio académico',
                    'Sostener la formación práctica de {carreras} mediante prácticas de laboratorio seguras, '
                    'planificadas y evaluadas, y apoyar la investigación formativa y los trabajos de titulación con '
                    'equipamiento y acompañamiento técnico.')],
        'objetivos_especificos': [('Laboratorio · prácticas',
                                   'Ejecutar las prácticas planificadas por asignatura con guía aprobada.\n'
                                   'Actualizar al menos una guía de práctica por asignatura atendida.\n'
                                   'Atender los trabajos de titulación y semilleros que requieran el laboratorio.')],
        'diagnostico': [('Laboratorio · estado',
                         'El laboratorio atiende … asignaturas y … estudiantes por período. Los equipos en uso cubren '
                         'las prácticas de …; los equipos en mantenimiento o dañados limitan …')],
    },
    'plantas_piloto': {
        'mision': [('Planta piloto',
                    'Formar en procesos productivos reales, escalar y validar productos y servicios para el sector '
                    'agroindustrial, y transferir tecnología al territorio bajo buenas prácticas de manufactura e '
                    'inocuidad.')],
        'objetivos_especificos': [('Planta · producción y servicios',
                                   'Ejecutar los lotes de producción y prácticas de proceso planificados con '
                                   'trazabilidad completa.\n'
                                   'Atender los servicios de maquila y análisis solicitados por el sector productivo.\n'
                                   'Cumplir el plan de limpieza, inocuidad y control de calidad de la planta.')],
        'politicas': [('Inocuidad',
                       'Ingreso a las áreas de proceso con indumentaria y lavado de manos según el procedimiento.\n'
                       'Registro de cada lote con materias primas, parámetros de proceso y controles de calidad.\n'
                       'Manejo de desechos y subproductos según el plan ambiental de la planta.')],
    },
    'centro_experimental': {
        'mision': [('Centro experimental',
                    'Servir de escenario de campo para la formación práctica, la investigación aplicada y la '
                    'transferencia de tecnología agropecuaria, con ensayos documentados y manejo sostenible de los '
                    'recursos.')],
        'objetivos_especificos': [('Centro · ensayos',
                                   'Establecer y evaluar los ensayos y parcelas experimentales planificados.\n'
                                   'Atender las prácticas de campo de las asignaturas vinculadas.\n'
                                   'Registrar la producción y el manejo de las unidades productivas del centro.')],
    },
    'observatorios': {
        'mision': [('Observatorio',
                    'Generar, sistematizar y difundir información y análisis sobre {tema} para orientar la toma de '
                    'decisiones de la academia, el sector público y la comunidad.')],
        'objetivos_especificos': [('Observatorio · productos',
                                   'Publicar los boletines o informes periódicos planificados.\n'
                                   'Mantener actualizadas las bases de datos e indicadores del observatorio.\n'
                                   'Realizar eventos de socialización de resultados con actores del territorio.')],
        'diagnostico': [('Observatorio · estado',
                         'El observatorio cuenta con … fuentes de información y … productos periódicos; las '
                         'limitaciones del período están en …')],
    },
    'centros_id': {
        'mision': [('Centro de investigación',
                    'Desarrollar investigación científica y tecnológica de alto impacto, formar investigadores y '
                    'transferir resultados a la sociedad mediante proyectos, publicaciones, redes y convenios.')],
        'objetivos_especificos': [('Centro I+D · resultados',
                                   'Mantener en ejecución los proyectos de investigación aprobados.\n'
                                   'Publicar artículos y ponencias en medios indexados.\n'
                                   'Gestionar convenios y redes de cooperación activas.')],
    },
}

POLITICA_POR_CAMPO = {
    'estructura': 'tablas', 'mobiliario': 'tablas', 'analisis_uso': 'tablas', 'diagnostico': 'tablas',
    'descripcion': 'tablas', 'resumen_ejecutivo': 'tablas',
}


def _contexto(unidad, documento):
    facultad = (unidad.facultad or 'facultad responsable').strip()
    return {
        'unidad': unidad.nombre,
        'tipo': unidad.nombre_tipologia or 'unidad',
        'facultad': facultad if facultad.lower().startswith('facultad') else f'Facultad {facultad}',
        'carreras': (unidad.carreras or 'las carreras que atiende').strip(),
        'periodo': documento.etiqueta_corte,
        'descripcion_ficha': (unidad.descripcion or '').strip() or 'Describe aquí la unidad.',
        'tema': 'su ámbito de observación',
    }


def sugerencias_para(documento, politicas):
    """{campo: [{'label', 'resumen', 'html'}]} con los textos ya escritos para la unidad."""
    if documento.exigido.fuente_reporte == 'protocolo':
        from .protocolo_seguridad import valores_iniciales
        return {clave: [dict(label='Redacción base para adaptar', resumen='Ajusta este texto a la unidad.', html=valor)]
                for clave, valor in valores_iniciales(documento).items()
                if isinstance(valor, str) and valor.startswith('<')}
    if documento.exigido.fuente_reporte == 'reglamento':
        from .reglamento_uso import sugerencias
        return sugerencias(documento)
    unidad = documento.unidad
    contexto = _contexto(unidad, documento)
    propias = POR_TIPO.get(unidad.codigo_base, {})
    resultado = {}
    for campo, comunes in COMUNES.items():
        opciones = list(propias.get(campo, [])) + list(comunes)
        politica = politicas.get(campo, 'texto')
        lista = []
        for etiqueta, plantilla in opciones:
            try:
                texto = plantilla.format(**contexto)
            except (KeyError, IndexError):
                texto = plantilla
            html = texto_a_html(texto, politica)
            if not html:
                continue
            resumen = texto.split('\n')[0].replace('## ', '')[:96]
            lista.append({'label': etiqueta, 'resumen': resumen, 'html': html})
        if lista:
            resultado[campo] = lista
    return resultado
