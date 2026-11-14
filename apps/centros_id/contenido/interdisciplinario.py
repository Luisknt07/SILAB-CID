"""Contrato de contenido para centros interdisciplinarios de la propuesta de tres centros.

Describe agendas y servicios sujetos a evaluación, sin acreditar creación oficial,
personal, equipamiento, resultados ni convenios que todavía no estén registrados.
"""
def lineas(*filas):
    return '\n'.join(' | '.join(fila) if isinstance(fila, (tuple, list)) else fila for fila in filas)



def construir(centro, areas, carreras, unidades, imagen, documentos):
    componentes, lineas_investigacion, servicios = [], [], []
    detalles_lineas, detalles_servicios, procesos = {}, {}, {}
    for orden, area in enumerate(areas, 1):
        codigo = area['codigo']
        pasos = area['pasos']
        componentes.append(dict(
            codigo=codigo, tipo='modulo', nombre=area['nombre'], nombre_corto=area['nombre'],
            icono=area['icono'], color=area['color'], orden=orden,
            resumen=area['resumen'], descripcion=area['descripcion'],
            funciones=lineas(*area['funciones']), capacidades=lineas(*area['capacidades']),
            resultados=lineas(*area['resultados']), flujo=lineas(*pasos),
            seguridad=lineas((area['riesgo'], area['control'])),
            software=lineas(*area.get('software', ())),
            unidades_articuladas='\n'.join(area.get('unidades', ())),
        ))
        nombre_linea = area['linea']
        lineas_investigacion.append((nombre_linea, area['evidencia'], codigo))
        detalles_lineas[nombre_linea] = dict(
            problema=area['problema'], objetivos=area['objetivos'], preguntas=area['preguntas'],
            metodologia=area['metodologia'], ambito='Carchi y región fronteriza; alcance definido por proyecto',
            retos='\n'.join(area['retos']),
        )
        procesos[codigo] = (area['proceso'], area['entrada'], area['salida'])
        for servicio in area['servicios']:
            nombre, incluye, entregable, entradas, alcance = servicio
            servicios.append((area['nombre'], codigo, nombre, incluye, entregable))
            detalles_servicios[nombre] = dict(
                alcance=alcance, entradas=entradas,
                requisitos=area['requisitos'], metodo=area['metodologia'],
                exclusiones=area['exclusiones'], condiciones=area['condiciones'],
                formato_entrega='Informe técnico y anexos acordados; devolución de resultados al solicitante.',
                plazo='Se acuerda tras evaluar el alcance, los insumos y la disponibilidad del equipo responsable.',
                aceptacion='Entregables completos según el plan aceptado, con método, resultados, límites y recomendaciones.',
                estado_oferta='consultar', modalidad='acompanamiento',
            )
    gobierno = (
        ('Dirección del centro', 'direccion', 'fas fa-landmark',
         'Coordina la agenda interdisciplinaria, los recursos compartidos y la rendición de cuentas.',
         lineas('Priorizar proyectos con criterios públicos de pertinencia y viabilidad.',
                'Designar responsables y asegurar seguimiento de compromisos.',
                'Coordinar acceso a capacidades sin duplicar la gestión de las unidades.')),
        ('Comité científico interdisciplinario', 'comite', 'fas fa-users',
         'Evalúa pertinencia, rigor metodológico, integridad y colaboración entre áreas.',
         lineas('Revisar preguntas, métodos, entregables y condiciones de transferencia.',
                'Identificar requisitos éticos y de seguridad antes de la ejecución.',
                'Evaluar resultados con evidencia y declarar conflictos de interés.')),
        ('Coordinación de áreas y servicios', 'coordinacion', 'fas fa-project-diagram',
         'Organiza equipos de proyecto, servicios y relación con las unidades vinculadas.',
         lineas('Evaluar solicitudes y documentar alcance, costos y plazos.',
                'Concertar reservas con la unidad propietaria y comprobar requisitos.',
                'Cerrar expedientes con entregables, aceptación y seguimiento.')),
    )
    ruta = (
        (1, 'Plantear la necesidad', 'Identificar problema, destinatarios, contexto y resultado esperado.',
         'Solicitante y coordinación de atención', 'Solicitud registrada y clasificación de la necesidad.'),
        (2, 'Evaluar viabilidad', 'Revisar pertinencia, capacidades, requisitos éticos y disponibilidad.',
         'Coordinación del área', 'Respuesta de viabilidad o derivación a la unidad competente.'),
        (3, 'Acordar el plan', 'Definir método, entregables, responsabilidades, costos, datos y plazos.',
         'Equipo responsable y solicitante', 'Plan de trabajo aceptado y condiciones documentadas.'),
        (4, 'Preparar recursos', 'Coordinar personal, inducciones, insumos y reservas con las unidades propietarias.',
         'Responsable del proyecto y unidad vinculada', 'Recursos y requisitos confirmados.'),
        (5, 'Ejecutar y verificar', 'Registrar actividades, observaciones, controles y cambios del plan.',
         'Equipo de proyecto', 'Resultados trazables y revisión técnica.'),
        (6, 'Entregar y acompañar', 'Explicar resultados, límites, recomendaciones y condiciones de aplicación.',
         'Equipo responsable y solicitante', 'Entregables aceptados y seguimiento acordado.'),
    )
    modalidades = (
        ('Investigación aplicada', 'Resolver preguntas con método y evidencia verificable.',
         'Investigadores, estudiantes, instituciones y organizaciones', 'fas fa-flask'),
        ('Servicios y acompañamiento', 'Evaluar y atender necesidades con alcance y entregables definidos.',
         'Comunidad universitaria, productores, empresas y entidades públicas', 'fas fa-hands-helping'),
        ('Formación y transferencia', 'Compartir métodos, resultados y capacidades mediante capacitación y trabajo conjunto.',
         'Carreras, profesionales y organizaciones del territorio', 'fas fa-graduation-cap'),
    )
    articulacion = tuple(('carrera', nombre, aporte, '') for nombre, aporte in carreras)
    articulacion += tuple(('unidad', nombre, aporte, slug) for slug, nombre, aporte in unidades)
    centro = dict(centro)
    centro['cadena'] = lineas(*((nombre, responsable, resultado) for _, nombre, _, responsable, resultado in ruta))
    return dict(
        CENTRO=centro, COMPONENTES=tuple(componentes), LINEAS=tuple(lineas_investigacion),
        SERVICIOS=tuple(servicios), DETALLES_LINEAS=detalles_lineas, DETALLES_SERVICIOS=detalles_servicios,
        GOBIERNO=gobierno, RUTA=ruta, MODALIDADES=modalidades, ARTICULACION=articulacion,
        VIDEOS={}, ZONAS=(), DOCUMENTOS=(), PROCESOS=procesos,
        IMAGENES=((imagen, '', 'Visualización conceptual de '+centro['nombre'],
                   'Visualización conceptual generada con IA (2026); no corresponde a una fotografía de instalaciones existentes.',
                   '', False, 1),),
        DOCUMENTOS_ENLACES=tuple(documentos),
    )
