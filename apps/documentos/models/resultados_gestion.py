"""Contrato de resultados documentados de laboratorios, sin copiar registros de Centros I+D."""
from datetime import date
import hashlib
import json

from .infraestructura import CLAVES_INFRAESTRUCTURA, TIPOS_INFRAESTRUCTURA, errores_infraestructura
from .funcionalidad import CLAVES_FUNCIONALIDAD, TIPO_FUNCIONALIDAD, errores_funcionalidad
from .resultados_perfiles import CLAVES_PERFIL, TIPOS_PERFIL, errores_perfil


TIPOS_PRODUCTO = (
    ('informe', 'Informe técnico o de investigación'),
    ('articulo', 'Artículo o ponencia'),
    ('prototipo', 'Prototipo o desarrollo tecnológico'),
    ('software', 'Software o simulador'),
    ('dataset', 'Datos, método o validación experimental'),
    ('titulacion', 'Producto de titulación o semillero'),
    ('servicio', 'Servicio especializado entregado'),
    ('transferencia', 'Tecnología o conocimiento transferido'),
    ('asistencia', 'Asistencia técnica o capacitación entregada'),
    ('otro', 'Otro producto verificable'),
)
TIPOS_RESULTADO = ('INVESTIGACION', 'TRANSFERENCIA')
TIPOS_ESTRUCTURADOS = (*TIPOS_RESULTADO, 'INSPECCION', *TIPOS_INFRAESTRUCTURA, TIPO_FUNCIONALIDAD, *TIPOS_PERFIL)
CLAVES_RESULTADO = ('proyecto', 'tipo_producto', 'producto', 'beneficiario',
                   'aceptacion', 'fecha_aceptacion', 'referencia_aceptacion')
CONDICIONES_REVISION = (
    ('infraestructura', 'Infraestructura, ventilación e iluminación'),
    ('equipos', 'Equipos, instalaciones eléctricas y protecciones'),
    ('emergencias', 'Emergencias, rutas de evacuación y señalización'),
    ('proteccion', 'Protección personal y bioseguridad'),
    ('almacenamiento', 'Almacenamiento de materiales, reactivos e insumos'),
    ('limpieza', 'Orden, limpieza y desinfección'),
    ('desechos', 'Segregación y almacenamiento de desechos'),
)
ESTADOS_CONDICIONES = (
    ('seguro', 'Sin condiciones inseguras detectadas en la revisión'),
    ('observado', 'Con observaciones que requieren seguimiento'),
    ('no_operar', 'No operar: condición insegura documentada'),
)
ESTADOS_ACCION = (('no_requiere', 'No requiere acción correctiva'),
                  ('pendiente', 'Acción pendiente'), ('resuelta', 'Acción atendida y respaldada'))
CLAVES_INSPECCION = ('area', 'condiciones_revisadas', 'sin_hallazgos', 'hallazgos',
                    'accion_correctiva', 'estado_condiciones', 'estado_accion', 'plazo_accion')
CLAVES_DETALLE = tuple(dict.fromkeys(CLAVES_RESULTADO + CLAVES_INSPECCION + CLAVES_INFRAESTRUCTURA + CLAVES_FUNCIONALIDAD + CLAVES_PERFIL + ('revision_criticidad',)))


def errores_inspeccion(detalle, fecha):
    """Documenta lo observado y su seguimiento; no concede permisos de operación."""
    if not isinstance(detalle, dict):
        return {'area': 'Identifica el área inspeccionada y las condiciones revisadas.'}
    errores = {}
    if not isinstance(detalle.get('area'), str) or not detalle['area'].strip():
        errores['area'] = 'Identifica el área o alcance que se inspeccionó.'
    elif len(detalle['area']) > 300:
        errores['area'] = 'Usa hasta 300 caracteres para el área o alcance.'
    condiciones = detalle.get('condiciones_revisadas')
    if (not isinstance(condiciones, list) or not condiciones or
            any(not isinstance(c, str) or c not in dict(CONDICIONES_REVISION) for c in condiciones)):
        errores['condiciones_revisadas'] = 'Indica las condiciones comprobadas en la inspección.'
    for clave in ('hallazgos', 'accion_correctiva'):
        valor = detalle.get(clave, '')
        if not isinstance(valor, str) or len(valor) > 3000:
            errores[clave] = 'Describe este campo con texto de hasta 3000 caracteres.'
    estado = detalle.get('estado_condiciones')
    if estado not in dict(ESTADOS_CONDICIONES):
        errores['estado_condiciones'] = 'Registra la condición documentada durante la inspección.'
    sin_hallazgos = detalle.get('sin_hallazgos') is True
    hallazgos = str(detalle.get('hallazgos') or '').strip()
    if sin_hallazgos:
        if estado != 'seguro' or hallazgos:
            errores['sin_hallazgos'] = 'Sin hallazgos corresponde a una revisión sin observaciones; no registres hallazgos contradictorios.'
        if detalle.get('estado_accion') != 'no_requiere':
            errores['estado_accion'] = 'Una inspección sin hallazgos debe indicar que no requiere acción correctiva.'
        if detalle.get('accion_correctiva') or detalle.get('plazo_accion'):
            errores['accion_correctiva'] = 'Una revisión sin hallazgos no debe registrar acciones o plazos contradictorios.'
    else:
        if not hallazgos:
            errores['hallazgos'] = 'Describe los hallazgos o marca explícitamente que no hubo hallazgos.'
        if estado == 'seguro':
            errores['estado_condiciones'] = 'Si existen hallazgos, registra las observaciones o la condición insegura.'
        if not str(detalle.get('accion_correctiva') or '').strip():
            errores['accion_correctiva'] = 'Describe la acción correctiva para los hallazgos detectados.'
        if detalle.get('estado_accion') not in ('pendiente', 'resuelta'):
            errores['estado_accion'] = 'Indica si la acción está pendiente o fue atendida con respaldo.'
    if detalle.get('estado_accion') == 'pendiente':
        try:
            plazo = date.fromisoformat(str(detalle.get('plazo_accion') or ''))
            if not fecha or plazo < fecha:
                raise ValueError
        except (ValueError, TypeError):
            errores['plazo_accion'] = 'Fija un plazo para la acción pendiente, igual o posterior a la inspección.'
    return errores


def errores_resultado(tipo, detalle, fecha):
    """Exige un producto ocurrido; una reserva o una intención no son un resultado."""
    if tipo in TIPOS_PERFIL:
        return errores_perfil(tipo, detalle, fecha)
    if tipo == 'INSPECCION':
        return errores_inspeccion(detalle, fecha)
    if tipo in TIPOS_INFRAESTRUCTURA:
        return errores_infraestructura(tipo, detalle, fecha)
    if tipo == TIPO_FUNCIONALIDAD:
        return errores_funcionalidad(detalle)
    if tipo not in TIPOS_RESULTADO:
        return {}
    if not isinstance(detalle, dict):
        return {'producto': 'Describe el producto obtenido y su respaldo verificable.'}
    errores = {}
    etiquetas = {'proyecto': 'Identifica el proyecto, trabajo o convenio relacionado.',
                 'producto': 'Identifica el producto o entregable que ya se obtuvo.',
                 'beneficiario': 'Identifica a la institución, grupo o persona destinataria.'}
    for clave, mensaje in etiquetas.items():
        if not isinstance(detalle.get(clave), str) or not detalle[clave].strip():
            errores[clave] = mensaje
        elif len(detalle[clave]) > 300:
            errores[clave] = 'Usa hasta 300 caracteres; amplía el resultado en la descripción.'
    if detalle.get('tipo_producto') not in dict(TIPOS_PRODUCTO):
        errores['tipo_producto'] = 'Selecciona el tipo de producto obtenido.'
    if tipo == 'TRANSFERENCIA':
        if detalle.get('aceptacion') != 'aceptado':
            errores['aceptacion'] = 'Para acreditar la transferencia debe existir aceptación del destinatario.'
        if not str(detalle.get('referencia_aceptacion') or '').strip():
            errores['referencia_aceptacion'] = 'Indica el acta, constancia o referencia que acredita la aceptación.'
        try:
            aceptacion = date.fromisoformat(str(detalle.get('fecha_aceptacion') or ''))
            if not fecha or aceptacion > fecha:
                raise ValueError
        except (ValueError, TypeError):
            errores['fecha_aceptacion'] = 'La aceptación debe tener fecha y ser anterior o igual a la evidencia.'
    return errores


def huella_resultado(evidencia):
    """Congela los datos que justificaron la verificación, además del archivo o enlace."""
    contenido = dict(codigo=evidencia.codigo, tipo=evidencia.tipo,
                     fecha=evidencia.fecha.isoformat() if evidencia.fecha else '',
                     titulo=evidencia.titulo, descripcion=evidencia.descripcion,
                     responsable=evidencia.responsable_id, detalle=evidencia.detalle)
    return hashlib.sha256(json.dumps(contenido, sort_keys=True, ensure_ascii=True).encode()).hexdigest()
