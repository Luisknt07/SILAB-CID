"""Reglamento de uso de la unidad: documento principal permanente, redactado con el editor guiado.

El texto estándar es el mismo para todas las unidades y solo cambia por tipo de unidad
(laboratorio, planta piloto, centro experimental y observatorio). Los datos que la
plataforma ya conoce (ficha, horario, aforo, personal, requisitos de acceso y contacto)
entran solos como bloques automáticos y se leen al mostrar y al generar.

Cuando la unidad envía una versión, su contenido se publica en ``ReglamentoUnidad`` y la
página pública muestra ese reglamento: el expediente es la única fuente de su texto.
"""
import html as html_lib
import re

from django.utils.html import escape, strip_tags

CODIGO = 'REGLAMENTO-USO'
FUENTE = 'reglamento'
NOMBRE = 'Reglamento de uso de la unidad'
NOMBRES_POR_BASE = {
    'laboratorios': 'Reglamento de uso del laboratorio',
    'plantas_piloto': 'Reglamento de uso de la planta piloto',
    'centro_experimental': 'Reglamento de uso del centro experimental',
    'observatorios': 'Reglamento de uso del observatorio',
}
REVISION = (('revisado', 'He revisado el texto propuesto y lo ajusté a las condiciones reales de esta unidad'),)

# Apartado del reglamento → campo de la publicación anterior (ReglamentoUnidad) que lo alimenta.
DESDE_PUBLICACION = {'conducta_reglamento': 'normas_generales', 'reservas_reglamento': 'reservas_horarios',
                     'recursos_reglamento': 'equipos_materiales', 'seguridad_reglamento': 'seguridad'}


def secciones(Campo, Seccion):
    return (
        Seccion('identificacion', 'Información general',
            'Datos de la ficha de la unidad. Se corrigen en su módulo de origen y se actualizan solos.',
            (), automatico='reglamento_general'),
        Seccion('alcance_reglamento', 'Objeto, alcance y usuarios',
            'Para qué existe el reglamento y a quiénes obliga.', (
                Campo('objeto_reglamento', 'Objeto y alcance', 'rico', True),
                Campo('usuarios_reglamento', 'Usuarios de la unidad', 'rico', True,
                    ayuda='Indica quiénes pueden usar la unidad y con qué autorización.'),
            )),
        Seccion('horario_reglamento', 'Horario de atención y reservas',
            'El horario y el aforo se toman de la configuración de la unidad.', (
                Campo('reservas_reglamento', 'Reservas, prioridades y cancelaciones', 'rico', True),
            ), automatico='reglamento_horario'),
        Seccion('acceso_reglamento', 'Acceso, requisitos y conducta',
            'Los requisitos de acceso registrados se muestran automáticamente.', (
                Campo('acceso_reglamento', 'Ingreso, inducción y vestimenta', 'rico', True),
                Campo('conducta_reglamento', 'Normas de conducta', 'rico', True),
            ), automatico='reglamento_acceso'),
        Seccion('recursos_reglamento', 'Uso de equipos, insumos y software',
            'Cómo se usan, se solicitan y se devuelven los recursos de la unidad.', (
                Campo('recursos_reglamento', 'Uso de los recursos', 'rico', True),
            )),
        Seccion('seguridad_reglamento', 'Seguridad, emergencias y residuos',
            'Reglas básicas; el detalle técnico está en el protocolo de seguridad de la unidad.', (
                Campo('seguridad_reglamento', 'Seguridad, emergencias y residuos', 'rico', True),
            )),
        Seccion('responsabilidades_reglamento', 'Responsabilidades, daños y sanciones',
            'Quién responde por qué y qué ocurre ante un incumplimiento.', (
                Campo('responsabilidades_reglamento', 'Responsabilidades', 'rico', True),
                Campo('danos_reglamento', 'Daños, pérdidas e incumplimientos', 'rico', True,
                    ayuda='Remite a la normativa institucional; no cites artículos ni resoluciones que no tengas a la vista.'),
            )),
        Seccion('contacto_reglamento', 'Contacto y vigencia',
            'El personal y sus contactos se toman de los registros de la unidad.', (
                Campo('contacto_reglamento', 'A quién acudir y vigencia del reglamento', 'rico', True),
            ), automatico='reglamento_contacto'),
        Seccion('firmas', 'Responsables del documento',
            'La emisión y la aprobación quedan atribuidas a los usuarios autenticados mediante el código QR.', (
                Campo('revision_propuestas', 'Revisión del texto propuesto', 'opcion', True, opciones=REVISION),
            )),
    )


# -- texto estándar ------------------------------------------------------------------------------

def _lista(*items):
    return '<ul>' + ''.join(f'<li>{escape(item)}</li>' for item in items if item) + '</ul>'


# Lo que cambia por tipo de unidad. Lo demás es común a todas.
PERFILES = {
    'laboratorios': dict(
        recursos='espacios, equipos, reactivos, insumos y software',
        actividades='prácticas, investigación, servicios y uso de equipos',
        vestimenta='Se usa la vestimenta y el equipo de protección personal que exige cada práctica (mandil, '
                   'gafas, guantes u otros indicados en la guía); sin ellos no se inicia la actividad.',
        prohibido='En las áreas de trabajo no se ingieren alimentos ni bebidas, no se fuma y no se manipulan '
                  'objetos personales mientras se trabaja con equipos o sustancias.',
        uso=('Cada equipo lo usa solo una persona capacitada, siguiendo su manual o instructivo; su estado se '
             'verifica antes y después de usarlo.',
             'Los reactivos e insumos se solicitan a la unidad, se usan en la cantidad necesaria y su consumo se '
             'registra en la plataforma.',
             'El software se usa con las licencias de la unidad y solo con fines académicos o institucionales; '
             'no se instalan programas sin autorización.',
             'Los préstamos de equipos fuera de la unidad se solicitan y se registran en la plataforma.'),
        residuos='Los residuos se separan y se depositan en los recipientes identificados; los residuos químicos '
                 'o peligrosos se entregan al responsable para su gestión, nunca se vierten al desagüe.',
    ),
    'plantas_piloto': dict(
        recursos='áreas de proceso, líneas y equipos, materias primas, insumos y software',
        actividades='procesos de producción, prácticas, servicios y uso de equipos',
        vestimenta='En las áreas de proceso se usa la indumentaria completa de la planta (uniforme limpio, cofia, '
                   'mascarilla y calzado cerrado), sin joyas ni objetos personales; las manos se lavan y '
                   'desinfectan al ingresar, conforme a las Buenas Prácticas de Manufactura.',
        prohibido='No ingresa a las áreas de proceso quien presente síntomas de enfermedad transmisible o heridas '
                  'sin proteger. No se consumen alimentos, bebidas ni tabaco fuera de las zonas destinadas.',
        uso=('Las líneas y los equipos de proceso los operan personas capacitadas, siguiendo su procedimiento, y '
             'se limpian y desinfectan antes y después de cada uso.',
             'Las materias primas e insumos ingresan identificados con su lote; su consumo se registra en la '
             'orden de producción.',
             'Ningún producto elaborado se consume, se entrega ni se retira sin la liberación del control de '
             'calidad.',
             'El software y los equipos de medición se usan solo para las actividades autorizadas de la planta.'),
        residuos='Los residuos de proceso, orgánicos y de limpieza se separan y se retiran de las áreas de '
                 'elaboración al terminar cada jornada; los residuos peligrosos se entregan al responsable.',
    ),
    'centro_experimental': dict(
        recursos='parcelas, instalaciones, maquinaria, animales, insumos agropecuarios y software',
        actividades='prácticas de campo, ensayos, producción agropecuaria y servicios',
        vestimenta='En el campo se usa ropa de trabajo, botas y la protección que exige la labor; la aplicación '
                   'de agroquímicos requiere el equipo de protección completo indicado en la etiqueta.',
        prohibido='No se ingresa a parcelas en ensayo, corrales ni bodegas sin la autorización del responsable. '
                  'No se consumen alimentos ni bebidas mientras se manipulan agroquímicos o animales.',
        uso=('La maquinaria agrícola y sus implementos los operan solo personas autorizadas y capacitadas, '
             'con la verificación previa de su estado.',
             'Los agroquímicos y los medicamentos veterinarios se aplican según su etiqueta y la indicación '
             'técnica del responsable, y cada aplicación se registra en la plataforma.',
             'Los animales se manejan según las indicaciones del responsable, evitando el dolor y el estrés '
             'innecesarios.',
             'Las parcelas y los ensayos identificados se respetan: no se cosecha, se muestrea ni se interviene '
             'sin autorización.'),
        residuos='Los envases vacíos de agroquímicos se lavan y se entregan al responsable; los residuos '
                 'orgánicos, pecuarios y peligrosos se manejan según el procedimiento del centro.',
    ),
    'observatorios': dict(
        recursos='datos, fuentes de información, equipos informáticos, software y espacios',
        actividades='análisis de información, publicaciones, atención de solicitudes y servicios',
        vestimenta='El ingreso a la sala y a los sistemas del observatorio se hace con las credenciales asignadas, '
                   'que son personales e intransferibles.',
        prohibido='No se ingieren alimentos ni bebidas junto a los equipos informáticos.',
        uso=('Los datos y las fuentes se usan citando su origen y respetando la política de datos del '
             'observatorio y la confidencialidad de la información.',
             'Ninguna base de datos, resultado preliminar o publicación se comparte fuera del observatorio sin '
             'la autorización del responsable.',
             'Los datos personales se tratan solo para el fin autorizado, conforme a la normativa aplicable.',
             'Los equipos y el software se usan con las licencias del observatorio; no se instalan programas ni '
             'se extrae información sin autorización, y el trabajo se respalda en los repositorios institucionales.'),
        residuos='Se protege la información: no se comparten contraseñas, se bloquea el equipo al ausentarse y se '
                 'informa de inmediato cualquier pérdida o acceso indebido. Los residuos electrónicos y de '
                 'impresión se entregan al responsable.',
    ),
}


def perfil_de(base):
    return PERFILES.get(base, PERFILES['laboratorios'])


def texto_estandar(unidad, base):
    """La redacción propuesta: igual para todas las unidades salvo lo propio de su tipo."""
    p = perfil_de(base)
    nombre = unidad.nombre
    observatorio = base == 'observatorios'
    objeto = ('Este reglamento establece las condiciones de acceso, reserva, uso, seguridad y responsabilidad que '
              f'rigen las actividades de {nombre}: {p["actividades"]}. Su cumplimiento es obligatorio para toda '
              f'persona que use sus {p["recursos"]}.')
    return {
        'objeto_reglamento': f'<p>{escape(objeto)}</p>',
        'usuarios_reglamento': _lista(
            'Estudiantes, docentes, investigadores y personal de la universidad, en actividades académicas, de '
            'investigación, vinculación o servicio autorizadas por la unidad.',
            'Usuarios externos y visitantes, con autorización previa del responsable de la unidad y bajo el '
            'acompañamiento que este disponga.',
            'Las personas que solicitan datos o información, conforme a la política de datos del observatorio.'
            if observatorio else ''),
        'reservas_reglamento': _lista(
            'La unidad atiende en el horario de operación publicado; fuera de él solo se trabaja con autorización '
            'del responsable.',
            'Las solicitudes de datos e información se presentan por la plataforma y se atienden en el orden y '
            'los plazos que fije el observatorio.' if observatorio else
            'Todo uso de espacios y equipos se reserva por la plataforma institucional, con la anticipación que '
            'fije la unidad; las prácticas planificadas tienen prioridad.',
            'El número de personas presentes no supera el aforo registrado de la unidad y de cada espacio.',
            'Quien no pueda asistir cancela su reserva con anticipación; las inasistencias reiteradas sin aviso '
            'pueden limitar nuevas reservas.'),
        'acceso_reglamento': _lista(
            'Ingresan solo las personas con reserva o autorización vigente que cumplen los requisitos de acceso '
            'de la unidad.',
            'Antes del primer uso, cada persona recibe la inducción de la unidad; sin ella no se autoriza el '
            'trabajo.',
            p['vestimenta']),
        'conducta_reglamento': _lista(
            p['prohibido'],
            'Se mantienen el orden, la limpieza y un trato respetuoso con las demás personas.',
            'Se siguen las indicaciones del personal responsable.' if observatorio else
            'Se siguen las indicaciones del personal responsable y, en las prácticas, las de su guía.',
            'Ningún bien, material o información sale de la unidad sin autorización registrada.'),
        'recursos_reglamento': _lista(
            *p['uso'],
            'Las fallas, daños o faltantes se informan de inmediato al responsable; nadie repara ni modifica un '
            'equipo sin autorización.'),
        'seguridad_reglamento': _lista(
            'Se cumple el protocolo de seguridad y condiciones de operación de la unidad.',
            'Antes de iniciar se identifican las salidas, las rutas de evacuación y los elementos de emergencia.',
            'Todo incidente, accidente o condición insegura se informa de inmediato al responsable y se registra '
            'en la plataforma.',
            p['residuos']),
        'responsabilidades_reglamento': _lista(
            'El responsable de la unidad hace cumplir este reglamento, autoriza el acceso y programa el uso.',
            'El docente o responsable de cada actividad supervisa a su grupo y responde por el cumplimiento '
            'durante la sesión.',
            'Cada usuario responde por el uso correcto de los recursos que se le asignan y los devuelve en las '
            'condiciones en que los recibió.'),
        'danos_reglamento': _lista(
            'El daño, la pérdida o el uso indebido de un bien se informa y se registra; quien lo cause por '
            'negligencia o mal uso responde por su reparación o reposición conforme a la normativa institucional.',
            'El incumplimiento de este reglamento puede suspender el acceso o las reservas de la persona y se '
            'comunica a la instancia que corresponda según la normativa institucional.'),
        'contacto_reglamento': '<p>' + escape(
            'Las consultas, solicitudes y reportes se dirigen al personal de la unidad por los medios de contacto '
            'indicados. Este reglamento rige desde su envío en la plataforma, se publica en la página de la '
            'unidad y se revisa cuando cambian sus condiciones de operación.') + '</p>',
    }


def _lineas_publicadas(texto):
    return [linea.strip() for linea in str(texto or '').splitlines() if linea.strip()]


def _publicacion_propia(unidad):
    """Lo que la unidad escribió en su reglamento publicado, si no es el texto genérico con el que nació."""
    from apps.recursos.models.recursos import REGLAMENTO_GENERICO, ReglamentoUnidad
    reglamento = ReglamentoUnidad.objects.filter(unidad=unidad).first() if unidad.pk else None
    if reglamento is None:
        return {}
    propio = {}
    for clave, campo in DESDE_PUBLICACION.items():
        lineas = _lineas_publicadas(getattr(reglamento, campo, ''))
        if lineas and lineas != _lineas_publicadas(REGLAMENTO_GENERICO.get(campo, '')):
            propio[clave] = _lista(*lineas)
    return propio


def _redaccion_anterior(documento):
    """La última versión emitida del reglamento de la unidad, para partir de ella en una versión nueva."""
    from apps.documentos.models.expediente import DocumentoElaborado
    if not documento.unidad_id:
        return {}
    anterior = (DocumentoElaborado.objects.filter(
        documento__unidad_id=documento.unidad_id, documento__exigido__codigo=CODIGO, generado_en__isnull=False)
        .exclude(documento_id=documento.pk).order_by('-generado_en').first())
    return dict(anterior.contenido or {}) if anterior else {}


def valores_iniciales(documento):
    from .perfil_unidades import base_de
    unidad = documento.unidad
    contenido = texto_estandar(unidad, base_de(unidad))
    anterior = _redaccion_anterior(documento)
    if anterior:
        contenido.update({clave: anterior[clave] for clave in contenido if anterior.get(clave)})
    else:
        # Lo que la unidad ya había escrito en su reglamento publicado es el punto de partida.
        contenido.update(_publicacion_propia(unidad))
    administrador = unidad.administrador
    contenido.update(firma_nombre=(administrador.get_full_name() or administrador.get_username()) if administrador else '',
                     firma_cargo='Responsable de la unidad', revision_propuestas='')
    return contenido


def sugerencias(documento):
    """El texto estándar del tipo de unidad, ofrecido en cada apartado para volver a él."""
    from .perfil_unidades import base_de
    return {clave: [dict(label='Texto estándar del reglamento', resumen='Redacción común a las unidades de este tipo.',
                         html=valor)]
            for clave, valor in texto_estandar(documento.unidad, base_de(documento.unidad)).items()}


# -- datos automáticos ---------------------------------------------------------------------------

def _aforo(unidad):
    return f'{unidad.capacidad_personas} personas' if unidad.capacidad_personas else 'Aforo pendiente en la ficha de la unidad'


def bloques_automaticos(documento, contenido=None):
    from .protocolo_contexto import contexto_de
    c = contexto_de(documento)
    identidad = c['identidad']
    resultado = dict(
        reglamento_general=[dict(tipo='pares', titulo='Ficha de la unidad', pares=[
            ('Nombre de la unidad', identidad['unidad_nombre']), ('Tipo de unidad', identidad['unidad_tipo']),
            ('Instalaciones y ubicación', identidad['ubicacion_protocolo']),
            ('Horario de atención', identidad['horario_protocolo']), ('Aforo', _aforo(documento.unidad)),
            ('Contacto', identidad['contacto_protocolo'])])],
        reglamento_horario=[dict(tipo='pares', titulo='Horario y aforo registrados', pares=[
            ('Horario de atención', identidad['horario_protocolo']), ('Aforo', _aforo(documento.unidad))])],
        reglamento_contacto=[dict(tipo='tabla', titulo='Personal de la unidad',
            cabecera=['Rol', 'Nombre', 'Contacto'],
            filas=[[p['rol'], p['nombre'], p['contacto'] or 'Contacto pendiente en la ficha de la unidad']
                   for p in c['personal']])],
    )
    resultado['reglamento_acceso'] = [dict(tipo='lista', titulo='Requisitos de acceso registrados',
        items=[r['nombre'] + (': ' + r['descripcion'] if r['descripcion'] else '') for r in c['requisitos']])
        if c['requisitos'] else dict(tipo='vacio', texto='La unidad no tiene requisitos de acceso registrados.')]
    return resultado


# -- publicación en la página de la unidad -------------------------------------------------------

def _lineas(html):
    """Una línea por párrafo o elemento de lista, en texto plano."""
    partes = re.split(r'</(?:p|li|h\d)>|<br\s*/?>', str(html or ''), flags=re.IGNORECASE)
    return [' '.join(html_lib.unescape(strip_tags(parte)).split()) for parte in partes
            if ' '.join(html_lib.unescape(strip_tags(parte)).split())]


def _corto(texto, limite):
    texto = ' '.join(texto.split())
    return texto if len(texto) <= limite else texto[:limite - 1].rsplit(' ', 1)[0] + '…'


def publicar(documento, usuario=None):
    """Lleva la versión enviada a ``ReglamentoUnidad``: la página pública muestra el reglamento oficial."""
    from apps.documentos.models.expediente import DocumentoElaborado
    from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
    from apps.recursos.models.recursos import ReglamentoUnidad
    redaccion = DocumentoElaborado.objects.filter(documento_id=documento.pk).first()
    if redaccion is None or not redaccion.generado_en or redaccion.generado_version != redaccion.version:
        return None  # Un PDF cargado sin redacción, o una redacción posterior al PDF enviado, no se publica.
    contenido = redaccion.contenido or {}
    unidad = documento.unidad
    from .protocolo_contexto import contexto_de
    identidad = contexto_de(documento)['identidad']
    normas = [linea for clave in ('usuarios_reglamento', 'acceso_reglamento', 'conducta_reglamento',
                                  'responsabilidades_reglamento', 'danos_reglamento')
              for linea in _lineas(contenido.get(clave))]
    reservas = [f"Horario de atención: {identidad['horario_protocolo']}.", f'Aforo: {_aforo(unidad)}.',
                *_lineas(contenido.get('reservas_reglamento'))]
    administrador = unidad.administrador
    datos = dict(
        titulo=_corto(f'{documento.nombre_documental}: {unidad.nombre}', 180),
        subtitulo=_corto(' '.join(_lineas(contenido.get('objeto_reglamento'))), 255),
        normas_generales='\n'.join(normas), reservas_horarios='\n'.join(reservas),
        equipos_materiales='\n'.join(_lineas(contenido.get('recursos_reglamento'))),
        seguridad='\n'.join(_lineas(contenido.get('seguridad_reglamento'))),
        contacto_texto=_corto(' '.join(_lineas(contenido.get('contacto_reglamento'))), 255),
        activo=True)
    correo = unidad.contacto_email or (administrador.email if administrador else '')
    if correo:
        datos['contacto_email'] = correo
    reglamento, _ = ReglamentoUnidad.objects.update_or_create(unidad=unidad, defaults=datos)
    registrar_auditoria(unidad=unidad, usuario=usuario, accion='actualizar', objeto=reglamento,
        descripcion=f'Reglamento de uso publicado desde el expediente (versión {documento.version})',
        nuevos=dict(documento_id=documento.pk, version=documento.version, recurso_id=documento.recurso_id))
    return reglamento


def emitido_en_expediente(unidad):
    """Si la página pública ya muestra un reglamento enviado desde el expediente."""
    from apps.documentos.models.expediente import DocumentoExpediente
    return DocumentoExpediente.objects.filter(unidad=unidad, exigido__codigo=CODIGO, estado='validado').exists()
