"""Agrupación visual de indicadores, sin modificar sus cálculos ni instantáneas."""
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()
GRUPOS = (
    ('obligatorio', 'Obligatorios'),
    ('opcional', 'Opcionales'),
    ('informativo', 'Anexos automáticos · sin meta independiente'),
    ('segun-programacion', 'Según programación · sin compromiso este período'),
    ('sin-definir', 'Por definir en planificación'),
    ('no-aplica', 'No aplican'),
)


@register.filter
def semaforo_avance(valor):
    """Color del avance hacia la meta completa; no cambia la nota ni su mínimo."""
    try:
        porcentaje = Decimal(str(valor))
        if not porcentaje.is_finite() or not 0 <= porcentaje <= 100:
            return 'neutro'
    except (InvalidOperation, TypeError, ValueError):
        return 'neutro'
    if porcentaje == 100:
        return 'verde'
    return 'amarillo' if porcentaje >= 50 else 'rojo'


@register.filter
def etiqueta_avance(valor):
    return {'rojo': 'Avance bajo: menos del 50 %',
            'amarillo': 'En progreso: del 50 % a menos del 100 %',
            'verde': 'Completo: 100 %',
            'neutro': 'Sin medición válida'}[semaforo_avance(valor)]


@register.filter
def es_unidad_auditable(unidad):
    """Comparte el alcance del control documental con las pantallas y formularios."""
    from apps.documentos.presentation.perfil_unidades import es_unidad_auditable as aplica
    return bool(unidad and aplica(unidad))


@register.filter
def exigencia_estilo(fila):
    if fila.get('estado') == 'Anexo automático':
        return 'informativo'
    exigencia = fila.get('exigencia', '')
    if exigencia == 'Según programación':
        return 'segun-programacion'
    if exigencia.startswith('Obligatorio') or exigencia == 'Comprometido en planificación':
        return 'obligatorio'
    if exigencia == 'Sin definir' or fila.get('definida') is False:
        return 'sin-definir'
    if exigencia == 'No aplica' or fila.get('aplica') is False:
        return 'no-aplica'
    if fila.get('exigible'):
        return 'obligatorio'
    if exigencia == 'Opcional' or fila.get('obligatoria') is False:
        return 'opcional'
    # Las instantáneas v1 no incluían exigencia; eran metas comprometidas.
    return 'obligatorio' if not exigencia and 'porcentaje' in fila else 'sin-definir'


@register.filter
def estado_meta(fila):
    estado = fila.get('estado', '')
    if estado == 'Cumple':
        return {'clase': 'cumple', 'icono': '✓'}
    if estado == 'No cumple':
        return {'clase': 'opcional' if exigencia_estilo(fila) == 'opcional' else 'no-cumple', 'icono': '!'}
    if estado.startswith('Pendiente'):
        return {'clase': 'pendiente', 'icono': '◷'}
    return {'clase': 'neutro', 'icono': '—'}


def _agrupar(elementos, indicadores):
    grupos = {codigo: [] for codigo, _ in GRUPOS}
    prioridad = {codigo: indice for indice, (codigo, _) in enumerate(GRUPOS)}
    for elemento in elementos:
        clases = [exigencia_estilo(fila) for fila in indicadores(elemento)]
        categoria = min(clases, key=prioridad.get) if clases else 'sin-definir'
        grupos[categoria].append(elemento)
    return [dict(codigo=codigo, titulo=titulo, elementos=grupos[codigo])
            for codigo, titulo in GRUPOS if grupos[codigo]]


@register.filter
def grupos_metas(filas):
    return _agrupar(filas, lambda fila: [fila])


@register.filter
def grupos_anexos(anexos):
    def indicadores(anexo):
        if isinstance(anexo, dict):
            if anexo.get('es_soporte_planificacion'):
                return [dict(estado='Anexo automático')]
            return anexo.get('detalle_indicadores', [])
        return getattr(anexo, 'indicadores_cierre', [])
    return _agrupar(anexos, indicadores)


# Lectura por temas de los anexos del informe. Siguen el orden del catálogo, así que cada tema queda junto.
CATEGORIAS_DE_ANEXOS = (
    ('Uso, equipamiento e inventario', ('REGISTRO-USO', 'EQUIPAMIENTO', 'INVENTARIO-CORTE')),
    ('Evidencias de las prácticas', ('FICHAS-TECNICAS', 'PRACTICAS-FT02', 'GUIAS', 'PRACTICAS-FT03')),
    ('Seguridad', ('INDUCCION-SEGURIDAD',)),
    ('Producción y calidad', ('PP-PRODUCCION', 'PP-CALIDAD')),
    ('Ensayos y producción agropecuaria', ('CE-ENSAYOS', 'CE-PRODUCCION')),
    ('Datos, publicaciones y socialización', ('OBS-DATOS', 'OBS-BOLETINES', 'OBS-EVENTOS')),
    ('Según la actividad del período: desechos, investigación y transferencia',
     ('DESECHOS', 'INVESTIGACION', 'TRANSFERENCIA')),
)
_CATEGORIA_POR_CODIGO = {codigo: titulo for titulo, codigos in CATEGORIAS_DE_ANEXOS for codigo in codigos}


def categoria_del_documento(bloque):
    """El tema bajo el que se lee un documento de la tabla de anexos."""
    if bloque.get('sin_anexo'):
        return 'Actividades sin anexo específico'
    if bloque.get('es_soporte_planificacion'):
        return 'Respaldos de la planificación'
    anexo = bloque.get('anexo')
    exigido = anexo.get('exigido') if isinstance(anexo, dict) else getattr(anexo, 'exigido', None)
    codigo = exigido.get('codigo') if isinstance(exigido, dict) else getattr(exigido, 'codigo', '')
    return _CATEGORIA_POR_CODIGO.get(codigo, 'Otros respaldos de la unidad')


# Metas del plan sin anexo cuyo respaldo es un documento propio del Centro de reportes: su categoría y su nombre.
_RESPALDO_DE_CAPACITACION = {'categoria': 'capacitacion', 'nombre': 'Capacitación del personal y difusión'}
RESPALDO_DE_METAS_SIN_ANEXO = {'CAPACITACION': _RESPALDO_DE_CAPACITACION, 'DIFUSION': _RESPALDO_DE_CAPACITACION}
# Lo que el Centro de reportes genera de los registros no va suelto: cada documento se lee en la categoría
# temática del anexo con el que se relaciona, o en una de las dos que solo tienen documentos generados.
# Las claves son las categorías de REPORT_FAMILIES; una nueva sin asignar cae en «Otros respaldos de la unidad».
CATEGORIA_PERSONAL = 'Personal, formación y difusión'
CATEGORIA_SEGUIMIENTO = 'Seguimiento y mejora'
CATEGORIA_SIN_ASIGNAR = 'Otros respaldos de la unidad'
_USO, _PRACTICAS, _SEGURIDAD = (titulo for titulo, _codigos in CATEGORIAS_DE_ANEXOS[:3])
_PRODUCCION, _SEGUN_ACTIVIDAD = CATEGORIAS_DE_ANEXOS[3][0], CATEGORIAS_DE_ANEXOS[-1][0]
CATEGORIA_DE_CONSULTA = {
    **dict.fromkeys(('reservas', 'uso-capacidad', 'mantenimiento', 'equipamiento', 'retiros', 'recursos',
                     'inventario', 'prestamos', 'visitas', 'calibracion', 'sustancias', 'satisfaccion'), _USO),
    **dict.fromkeys(('asignaturas', 'planificaciones', 'ejecuciones', 'aula', 'guias'), _PRACTICAS),
    **dict.fromkeys(('seguridad', 'desechos', 'simulacros'), _SEGURIDAD),
    **dict.fromkeys(('personal', 'capacitacion', 'cursos'), CATEGORIA_PERSONAL),
    **dict.fromkeys(('produccion', 'procesos', 'calidad', 'control-calidad'), _PRODUCCION),
    # Las fuentes propias de centros experimentales y observatorios (reportes_perfiles.CATEGORIAS_PERFIL).
    **dict.fromkeys(('ensayos', 'produccion-agropecuaria'), CATEGORIAS_DE_ANEXOS[4][0]),
    **dict.fromkeys(('boletines', 'datos-observatorio', 'eventos'), CATEGORIAS_DE_ANEXOS[5][0]),
    **dict.fromkeys(('investigacion', 'transferencia', 'finanzas'), _SEGUN_ACTIVIDAD),
    **dict.fromkeys(('mejora', 'auditoria'), CATEGORIA_SEGUIMIENTO),
}
# El orden en que se leen las categorías. Una que solo tiene documentos generados entra antes de la primera
# categoría de anexos que va después de ella; los anexos conservan su orden, que es el del informe.
ORDEN_DE_CATEGORIAS = (
    'Respaldos de la planificación', _USO, _PRACTICAS, _SEGURIDAD, CATEGORIA_PERSONAL,
    *(titulo for titulo, _codigos in CATEGORIAS_DE_ANEXOS[3:]),
    CATEGORIA_SIN_ASIGNAR, 'Actividades sin anexo específico', CATEGORIA_SEGUIMIENTO,
)
# Las dos clases de documento generado: (clave del filtro de exigencia, etiqueta de la fila).
EXIGENCIAS_DE_CONSULTAS = (('respaldo', 'Respaldo para auditoría'), ('gestion', 'Consulta de gestión'))


def categoria_de_consulta(consulta):
    return CATEGORIA_DE_CONSULTA.get(consulta.get('codigo'), CATEGORIA_SIN_ASIGNAR)


def _lectura_de_consulta(consulta):
    """La consulta con su categoría, su exigencia y su estado: así la fila no queda vacía."""
    clave = 'respaldo' if consulta.get('respaldo') else 'gestion'
    con_registros = consulta.get('con_registros')
    return dict(consulta, categoria=categoria_de_consulta(consulta), exigencia_clave=clave,
                etiqueta=dict(EXIGENCIAS_DE_CONSULTAS)[clave],
                registrado=consulta.get('registrado') or 'Se genera al consultar',
                estado=('Con registros' if con_registros else 'Sin registros en el período'
                        if con_registros is False else 'Disponible'))


def _posicion(categoria):
    return ORDEN_DE_CATEGORIAS.index(categoria) if categoria in ORDEN_DE_CATEGORIAS else None


@register.simple_tag
def filas_de_la_tabla(grupos, consultas=None):
    """Los anexos en el orden del informe y, al final de su categoría, los documentos generados de ese tema.

    Cada fila es `{'categoria', 'bloque'}` (un anexo o actividad) o `{'categoria', 'consulta'}`.
    """
    pendientes = {}
    for consulta in consultas or []:
        lectura = _lectura_de_consulta(consulta)
        pendientes.setdefault(lectura['categoria'], []).append(lectura)
    filas = []

    def volcar(categoria):
        filas.extend(dict(categoria=categoria, consulta=c) for c in pendientes.pop(categoria, []))

    def volcar_anteriores(posicion):
        for categoria in sorted((c for c in pendientes if (_posicion(c) or 0) < posicion), key=_posicion):
            volcar(categoria)

    anterior = None
    for bloque in en_orden(grupos):
        categoria = bloque['categoria']
        if categoria != anterior:
            if anterior is not None:
                volcar(anterior)
            posicion = _posicion(categoria)
            if posicion:
                volcar_anteriores(posicion)
            anterior = categoria
        filas.append(dict(categoria=categoria, bloque=bloque))
    if anterior is not None:
        volcar(anterior)
    volcar_anteriores(len(ORDEN_DE_CATEGORIAS))
    primera = next((fila for fila in filas if 'consulta' in fila), None)
    if primera:
        primera['primera_consulta'] = True
    return filas


@register.simple_tag
def exigencias_de_consultas(consultas):
    """Las opciones del filtro de exigencia para los documentos generados que hay en la tabla."""
    presentes = {'respaldo' if c.get('respaldo') else 'gestion' for c in consultas or []}
    return [(clave, etiqueta) for clave, etiqueta in EXIGENCIAS_DE_CONSULTAS if clave in presentes]


@register.filter
def consultas_por_categoria(consultas):
    """Las consultas sin tabla de anexos, en las mismas categorías temáticas y en su orden."""
    return [dict(categoria=categoria, consultas=[fila['consulta'] for fila in filas])
            for categoria, filas in _agrupadas(filas_de_la_tabla([], consultas))]


def _agrupadas(filas):
    grupos = []
    for fila in filas:
        if not grupos or grupos[-1][0] != fila['categoria']:
            grupos.append((fila['categoria'], []))
        grupos[-1][1].append(fila)
    return grupos


@register.simple_tag
def evidencias_cierre(cierre, anexos):
    """Una proyección de metas y archivos; no cambia cálculos ni datos enviados."""
    bloques, representados = [], set()
    for anexo in anexos or []:
        extras = {}
        if isinstance(anexo, dict):
            nombre, recurso = anexo['nombre'], anexo.get('recurso')
            indicadores = anexo.get('detalle_indicadores', [])
            extras = {k: anexo.get(k) for k in
                      ('documento_padre', 'entrega_padre', 'es_soporte_planificacion', 'origen_documental')}
            objeto_anexo = anexo.get('anexo', anexo)
        else:
            nombre, recurso = getattr(anexo, 'nombre_documental', anexo.exigido.nombre), anexo.recurso_id
            indicadores = getattr(anexo, 'indicadores_cierre', [])
            objeto_anexo = anexo
        representados.update(f['codigo'] for f in indicadores if f.get('codigo'))
        bloques.append(dict(nombre=nombre, recurso=recurso, anexo=objeto_anexo,
                            detalle_indicadores=indicadores, sin_anexo=False, **extras))
    for fila in (cierre or {}).get('filas', []):
        if fila.get('codigo') not in representados:
            lectura = dict(fila)
            lectura.setdefault('indicador', fila['nombre'])
            if 'exigencia' not in lectura:
                lectura['exigencia'] = 'Comprometido en planificación'
                lectura.setdefault('estado', 'Pendiente de medición' if fila.get('pendiente') else
                                   'Cumple' if fila.get('porcentaje') == 100 else 'No cumple')
            bloques.append(dict(nombre=fila['nombre'], recurso=None, anexo=None,
                                detalle_indicadores=[lectura], sin_anexo=True,
                                respaldo_auditoria=RESPALDO_DE_METAS_SIN_ANEXO.get(fila.get('codigo'))))
    grupos = grupos_anexos(bloques)
    # El número es el del anexo en el informe: el orden del expediente, no el del grupo.
    for numero, bloque in enumerate(bloques, 1):
        bloque['numero_item'] = numero
        bloque['categoria'] = categoria_del_documento(bloque)
    for grupo in grupos:
        for bloque in grupo['elementos']:
            bloque['grupo_codigo'] = grupo['codigo']
    return grupos


@register.filter
def en_orden(grupos):
    """Los documentos en una sola lista, en el orden del informe."""
    return sorted((bloque for grupo in grupos or [] for bloque in grupo['elementos']),
                  key=lambda bloque: bloque['numero_item'])


@register.simple_tag
def anexos_del_periodo(periodo):
    """Una tabla de lectura, conservando el padre y el circuito de cada anexo."""
    entregas = periodo.get('entregas', [])
    cierre = next((e for e in entregas if e.get('cierre')), {})
    anexos = []
    for entrega in entregas:
        padre = entrega['documento']
        soporte = padre.exigido.codigo == 'PLANIFICACION'
        # El orden del catálogo es el número que cada anexo lleva en el informe.
        for anexo in sorted(entrega.get('anexos', []),
                            key=lambda a: (getattr(a.exigido, 'orden', 0) or 0, a.exigido.codigo)):
            anexos.append(dict(nombre=anexo.nombre_documental, recurso=anexo.recurso_id,
                anexo=anexo, documento_padre=padre, entrega_padre=entrega,
                es_soporte_planificacion=soporte,
                origen_documental='Planificación' if soporte else 'Informe de cierre',
                # El consolidado de prácticas respalda la planificación; no duplica su meta.
                detalle_indicadores=[] if soporte else getattr(anexo, 'indicadores_cierre', [])))
    return dict(anexos=anexos, cierre=cierre.get('cierre', {}), entrega=cierre,
                documento=cierre.get('documento'))


@register.simple_tag
def consultas_en_la_tabla(periodos, corte, consultas):
    """Con un período elegido, las consultas van como última categoría de su tabla de anexos."""
    if not consultas or not corte:
        return False
    for periodo in periodos or []:
        if periodo.get('corte') == corte:
            tabla = anexos_del_periodo(periodo)
            return bool(tabla['anexos'] or tabla['cierre'])
    return False


@register.filter
def cantidad_items(grupos):
    return sum(len(grupo['elementos']) for grupo in grupos)


@register.filter
def clasificacion_meta(fila):
    """Clasifica el avance visible, sin sustituir el estado ni la evaluación."""
    if (fila.get('aplica') is False or fila.get('estado') in (
            'No aplica', 'Anexo automático', 'Según programación', 'Sin definir en planificación')
            or fila.get('exigencia') in ('No aplica', 'Sin definir', 'Según programación')):
        return 'neutro'
    if fila.get('pendiente') or str(fila.get('estado', '')).startswith('Pendiente'):
        return 'pendiente'
    try:
        porcentaje = Decimal(str(fila.get('porcentaje')))
        if not porcentaje.is_finite() or not 0 <= porcentaje <= 100:
            return 'pendiente'
    except (InvalidOperation, TypeError, ValueError):
        return 'pendiente'
    if porcentaje == 100:
        return 'cumple'
    return 'parcial' if porcentaje > 0 else 'sin-avance'


@register.simple_tag
def resumen_metas_cierre(grupos):
    """Cuenta metas obligatorias únicas de la misma proyección que muestra la tabla."""
    conteo = dict(cumplidas=0, parciales=0, sin_acreditar=0, pendientes=0, total=0)
    representadas = set()
    for grupo in grupos:
        for bloque in grupo['elementos']:
            for fila in bloque.get('detalle_indicadores', []):
                if exigencia_estilo(fila) != 'obligatorio':
                    continue
                codigo = fila.get('codigo')
                if codigo and codigo in representadas:
                    continue
                if codigo:
                    representadas.add(codigo)
                conteo['total'] += 1
                estado = clasificacion_meta(fila)
                if estado == 'cumple':
                    conteo['cumplidas'] += 1
                elif estado == 'parcial':
                    conteo['parciales'] += 1
                else:
                    conteo['sin_acreditar'] += 1
                    conteo['pendientes'] += estado == 'pendiente'
    for clave in ('cumplidas', 'parciales', 'sin_acreditar'):
        conteo[f'{clave}_porcentaje'] = (
            Decimal(conteo[clave]) * 100 / conteo['total'] if conteo['total'] else Decimal(0))
    return conteo
