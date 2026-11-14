"""Estructura editable del protocolo permanente, sin inventar condiciones verificadas."""
from django.utils.html import escape

NOMBRE = 'Protocolo de seguridad y condiciones de operación'
NOMBRE_ANTERIOR = 'Protocolo de bioseguridad y condiciones de operación'
FUENTE = 'protocolo'

AMBITOS = ('Agentes biológicos', 'Sustancias químicas', 'Equipos, máquinas y energía',
           'Actividades de campo', 'Información y datos')
APLICABILIDAD = (('si', 'Aplica'), ('no', 'No aplica'))


def secciones(Campo, Seccion):
    return (
        Seccion('identificacion', 'Información general',
            'Estos datos se toman de la ficha y de los horarios registrados. Se actualizan en su módulo de origen.',
            (), automatico='protocolo_general'),
        Seccion('alcance_protocolo', 'Objeto y alcance',
            'Delimita las personas, espacios y actividades que cubre el protocolo.', (
                Campo('objeto_protocolo', 'Objeto', 'rico', True),
                Campo('alcance_protocolo', 'Alcance y actividades comprendidas', 'rico', True,
                    ayuda='Incluye usuarios, personal, visitantes y contratistas cuando corresponda; identifica exclusiones.'),
            )),
        Seccion('responsables_protocolo', 'Organización y responsabilidades',
            'El personal, sus funciones y sus contactos se toman de los registros de la unidad.', (
                Campo('responsabilidades_adicionales', 'Funciones complementarias, si corresponde', 'rico'),
            ), automatico='protocolo_responsables'),
        Seccion('riesgos_protocolo', 'Identificación de peligros y controles',
            'Revisa las propuestas basadas en los espacios, equipos e insumos registrados. Ajusta las medidas y selecciona si cada actividad aplica.', (
                Campo('riesgos_protocolo', 'Peligros y medidas preventivas', 'tabla', True, columnas=(
                    ('aplica', 'Aplicabilidad', 'opcion', APLICABILIDAD),
                    ('actividad', 'Actividad o área', 'texto', ()),
                    ('peligro', 'Peligro y posible daño', 'multilinea', ()),
                    ('control', 'Medidas preventivas', 'multilinea', ()),
                    ('responsable', 'Responsable', 'responsable', ()),
                    ('verificacion', 'Cómo se verifica', 'multilinea', ()),
                )),
            )),
        Seccion('operacion_protocolo', 'Acceso y operación segura',
            'Describe las reglas de acceso y la secuencia de trabajo de la unidad.', (
                Campo('acceso_protocolo', 'Ingreso, autorización e inducción', 'rico', True),
                Campo('operacion_protocolo', 'Antes, durante y después de la actividad', 'rico', True,
                    ayuda='Precisa verificaciones previas, supervisión, protección, restricciones y cierre; vincula manuales específicos.'),
                Campo('suspension_protocolo', 'Suspensión y reanudación de actividades', 'rico', True,
                    ayuda='Indica cuándo se detiene la actividad, a quién se informa y quién autoriza su reanudación.'),
            ), automatico='protocolo_acceso'),
        Seccion('medidas_protocolo', 'Medidas específicas según las actividades',
            'Para cada ámbito indica las medidas aplicables o el motivo por el que no corresponde. Puedes añadir otros ámbitos.', (
                Campo('medidas_protocolo', 'Aplicabilidad y medidas específicas', 'tabla', True, columnas=(
                    ('ambito', 'Ámbito', 'texto', ()),
                    ('aplica', 'Aplicabilidad', 'opcion', APLICABILIDAD),
                    ('medidas', 'Medidas o justificación de no aplicación', 'multilinea', ()),
                )),
                Campo('limpieza_protocolo', 'Orden, limpieza y gestión de residuos', 'rico', True,
                    ayuda='Define responsables, frecuencia y manejo de los residuos que realmente se generan.'),
            )),
        Seccion('emergencias_protocolo', 'Emergencias y comunicación',
            'Completa la respuesta y los contactos reales de las instalaciones.', (
                Campo('emergencias_protocolo', 'Situaciones y respuesta inicial', 'tabla', True, columnas=(
                    ('situacion', 'Situación', 'texto', ()), ('respuesta', 'Actuación y comunicación', 'multilinea', ()),
                    ('aplica', 'Aplicabilidad', 'opcion', APLICABILIDAD),
                    ('responsable', 'Responsable', 'responsable', ()), ('recursos', 'Recursos previstos para la respuesta', 'multilinea', ()),
                )),
                Campo('evacuacion_protocolo', 'Alarma, evacuación y punto de encuentro', 'rico', True,
                    ayuda='Usa las rutas y el plan de emergencia vigentes de la instalación; no presupongas recursos disponibles.'),
                Campo('contactos_emergencia', 'Otros contactos de emergencia, si corresponde', 'tabla', columnas=(
                    ('servicio', 'Persona o servicio', 'texto', ()),
                    ('telefono', 'Teléfono, extensión o canal de aviso', 'texto', ()),
                    ('ubicacion', 'Ubicación o canal alterno', 'texto', ()),
                )),
            ), automatico='protocolo_contactos'),
        Seccion('seguimiento_protocolo', 'Capacitación, seguimiento y actualización',
            'Define cómo se comunica, se comprueba y se mantiene vigente este protocolo.', (
                Campo('induccion_protocolo', 'Inducción y comunicación a los usuarios', 'rico', True),
                Campo('controles_protocolo', 'Controles y registros', 'tabla', True, columnas=(
                    ('control', 'Control', 'texto', ()), ('frecuencia', 'Cuándo se realiza', 'frecuencia', ()),
                    ('responsable', 'Responsable', 'responsable', ()), ('registro', 'Registro de respaldo', 'texto', ()),
                )),
                Campo('revision_protocolo', 'Vigencia y criterios de actualización', 'rico', True),
                Campo('referencias_protocolo', 'Documentos de referencia y anexos', 'rico',
                    ayuda='Identifica únicamente las normas, manuales, fichas y planes que se utilicen, con su fecha o enlace.'),
            ), automatico='protocolo_instrucciones'),
        Seccion('firmas', 'Responsables del documento',
            'La emisión y la aprobación quedan atribuidas a los usuarios autenticados mediante el código QR.', (
                Campo('revision_propuestas', 'Revisión del contenido propuesto', 'opcion', True, opciones=(
                    ('revisado', 'He revisado la aplicabilidad, las medidas y los datos específicos de esta unidad'),)),
            )),
    )


def valores_iniciales(documento):
    from .perfil_unidades import base_de
    unidad = documento.unidad
    base = base_de(unidad)
    actividades = {
        'laboratorios': 'prácticas, investigación, servicios y uso de equipos e instalaciones',
        'plantas_piloto': 'procesos de producción, prácticas, servicios y uso de instalaciones',
        'centro_experimental': 'ensayos, prácticas y actividades de campo e instalaciones experimentales',
        'observatorios': 'análisis de información, publicaciones, servicios y trabajo en instalaciones',
    }.get(base, 'actividades y servicios de la unidad')
    def p(texto):
        return f'<p>{escape(texto)}</p>' if texto else ''
    administrador = unidad.administrador
    nombre = (administrador.get_full_name() or administrador.get_username()) if administrador else ''
    contacto = unidad.contacto_email or (administrador.email if administrador else '')
    contenido = {
        'unidad_nombre': unidad.nombre,
        'unidad_tipo': unidad.nombre_tipologia or base.replace('_', ' ').title(),
        'ubicacion_protocolo': p(unidad.ubicacion),
        'horario_protocolo': unidad.horario_atencion,
        'contacto_protocolo': contacto,
        'objeto_protocolo': p(f'Establecer las responsabilidades, medidas preventivas y condiciones de operación segura de {unidad.nombre}.'),
        'alcance_protocolo': p(f'Comprende las actividades de {unidad.nombre}: {actividades}, así como al personal, usuarios y visitantes que participen en ellas.'),
        'responsables_protocolo': [dict(rol='Responsable de la unidad', nombre=nombre,
            funcion='Coordinar la aplicación, comunicación y actualización del protocolo.', contacto=contacto)],
        'acceso_protocolo': p('El responsable autoriza el ingreso según la actividad, la capacidad del espacio y la formación requerida. '
            'Antes del acceso se comunican los riesgos, las restricciones y las medidas aplicables. '
            'Los visitantes y contratistas reciben las indicaciones y el acompañamiento que correspondan.'),
        'operacion_protocolo': (
            '<ol><li>Antes de iniciar, confirmar la autorización, las condiciones del espacio y los recursos necesarios; '
            'revisar los controles definidos para la actividad y los manuales aplicables.</li>'
            '<li>Durante la actividad, respetar los procedimientos autorizados, las restricciones y la supervisión definida. '
            'Comunicar cualquier condición insegura o desviación.</li>'
            '<li>Al finalizar, dejar el espacio y los recursos en las condiciones previstas para su siguiente uso '
            'y registrar las novedades y la entrega al responsable.</li></ol>'),
        'suspension_protocolo': p('Suspender la actividad ante un riesgo no controlado, una falla o un incidente que comprometa '
            'la seguridad. Comunicarlo al responsable y restringir el uso afectado. '
            'La reanudación requiere comprobar la corrección de las causas y la autorización del responsable designado.'),
        'limpieza_protocolo': p('Mantener despejadas las áreas de circulación y trabajo. Definir la limpieza según la actividad '
            'y las instrucciones aplicables. Separar, identificar y almacenar los residuos de acuerdo con su clasificación; '
            'los residuos peligrosos requieren el procedimiento específico de la unidad. Registrar las incidencias y su tratamiento.'),
        'induccion_protocolo': p('Antes de asignar una actividad, comunicar su alcance, riesgos, medidas preventivas, restricciones '
            'y respuesta ante emergencias. Conservar el registro de la inducción y verificar la comprensión de las indicaciones. '
            'Actualizar la información cuando cambien las actividades o las condiciones de trabajo.'),
        'revision_protocolo': p('Revisar el protocolo cuando cambien las actividades, instalaciones, equipos o riesgos, '
            'cuando un incidente o una inspección identifique medidas insuficientes, o cuando se actualicen las disposiciones aplicables. '
            'Comunicar los cambios al personal y a los usuarios antes de su aplicación.'),
        'firma_nombre': nombre, 'firma_cargo': 'Responsable de la unidad',
    }
    from .protocolo_contexto import completar_contenido
    # Las tablas se proponen desde los registros actuales, sin tablas vacías de ejemplo.
    return completar_contenido(documento, contenido, proponer=True)


def campo_completo(campo, valor):
    """Una fila prellenada o una celda suelta no completan una tabla obligatoria."""
    if campo.tipo != 'tabla':
        return None
    if not isinstance(valor, list) or not valor or not all(isinstance(fila, dict) for fila in valor):
        return False
    # La fila vacía que deja el editor no es una actividad declarada. Los
    # metadatos de las propuestas tampoco convierten una fila vacía en válida.
    filas = [fila for fila in valor if any(str(fila.get(clave) or '').strip()
                                         for clave, *_ in campo.columnas)]
    return bool(filas) and all(all(
        not isinstance(fila.get(clave), (dict, list, tuple, set, bool))
        and str(fila.get(clave) or '').strip() and (tipo != 'opcion' or fila[clave] in dict(opciones))
        for clave, _etiqueta, tipo, opciones in campo.columnas
        if not (fila.get('aplica') == 'no' and campo.clave in ('riesgos_protocolo', 'emergencias_protocolo')
                and clave not in ('aplica', 'actividad', 'situacion', 'control', 'respuesta')))
        for fila in filas)
