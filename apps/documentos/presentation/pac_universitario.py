"""Necesidades anuales y matriz de transferencia al formato universitario.

La matriz registra requerimientos. No concede financiamiento ni declara una
contratación aprobada; los códigos administrativos desconocidos quedan vacíos.
"""
from copy import deepcopy
from decimal import Decimal, DecimalException
from io import BytesIO
from itertools import zip_longest
import json
from html import unescape
from math import ceil
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from django.core.exceptions import ValidationError
from django.utils.html import strip_tags

from .presupuesto_documental import CATEGORIAS_INVERSION, FUENTES_FINANCIAMIENTO, PRIORIDADES


CLASIFICACIONES_PAC = (('por_definir', 'Por definir'), ('pac', 'PAC'), ('no_pac', 'NO PAC'))
PAC_VERSION = 2
VERSIONES_PAC = (1, PAC_VERSION)
CLASES_BIEN_LEGADO = (('equipos', 'Equipos'), ('software', 'Software'), ('materiales', 'Materiales'),
    ('insumos', 'Insumos'), ('reactivos', 'Reactivos'), ('servicios', 'Servicios de soporte'))
CLASES_BIEN = (('equipos', 'Equipos'), ('software', 'Software y licencias'),
    ('materiales', 'Materiales'), ('insumos', 'Insumos'), ('reactivos', 'Reactivos'),
    ('repuestos', 'Repuestos y accesorios'), ('servicios', 'Servicios de soporte'))
TIPOS_NECESIDAD = (('reposicion', 'Reposición'), ('dotacion', 'Dotación inicial'),
    ('ampliacion', 'Ampliación de capacidad'), ('mantenimiento', 'Mantenimiento'),
    ('insumos', 'Insumos y materiales'), ('otro', 'Otra necesidad'))
MESES_COMPRA = tuple((str(n), nombre) for n, nombre in enumerate((
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto',
    'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'), 1))
FUENTES_REFERENCIA = (('001', 'Recursos fiscales'), ('002', 'Recursos generados por instituciones'),
                     ('003', 'Recursos provenientes de preasignaciones'))
COLUMNAS_PAC = (
    ('area_id', 'Área de destino', 'opcion', ()),
    ('tipo_necesidad', 'Motivo de la adquisición', 'opcion', TIPOS_NECESIDAD),
    ('clase_bien', 'Clase de bien o servicio', 'opcion', CLASES_BIEN),
    ('item', 'Bien o servicio', 'texto', ()),
    ('especificaciones', 'Especificaciones del bien o servicio', 'texto', ()),
    ('unidad_medida', 'Unidad de medida', 'texto', ()),
    ('incidencia_referencia', 'Incidencia técnica de referencia', 'texto', ()),
    ('diagnostico_referencia', 'Diagnóstico técnico de referencia', 'texto', ()),
    ('cantidad', 'Cantidad', 'numero', ()),
    ('costo_unitario', 'Valor unitario (USD)', 'numero', ()),
    ('justificacion', 'Justificación de la necesidad', 'texto', ()),
    ('mes_compra', 'Mes previsto de adquisición', 'opcion', MESES_COMPRA),
    ('equipos_referencia', 'Equipos actuales relacionados', 'texto', ()),
    ('grupo_fases', 'Proyecto o conjunto de compras', 'texto', ()),
    ('fase_numero', 'Número de fase', 'numero', ()),
    ('resultado_fase', 'Resultado verificable de la fase', 'texto', ()),
    ('condicion_siguiente_fase', 'Condición para continuar a la siguiente fase', 'texto', ()),
    ('cpc', 'CPC', 'texto', ()),
    ('partida', 'Partida presupuestaria', 'texto', ()),
    ('clasificacion_pac', 'PAC / NO PAC', 'opcion', CLASIFICACIONES_PAC),
    ('fuente_pac', 'Fuente de financiamiento universitaria', 'texto', ()),
    ('observaciones', 'Observaciones', 'texto', ()),
    # Compatibilidad: estos datos internos no equivalen a las clasificaciones
    # universitarias y no se inventan al migrar una redacción anterior.
    ('categoria', 'Categoría interna', 'opcion', CATEGORIAS_INVERSION),
    ('prioridad', 'Prioridad interna', 'opcion', PRIORIDADES),
    ('fuente', 'Fuente interna', 'opcion', FUENTES_FINANCIAMIENTO),
    ('trimestre', 'Trimestre previsto', 'opcion', tuple((str(n), str(n)) for n in range(1, 5))),
)
ENCABEZADOS_CONSOLIDADO = ('N°', 'CENTRO DE COSTO', 'CENTRO DE COSTO', 'NOMBRE DEL BIEN O SERVICIO',
    'CANTIDAD', 'V. UNITARIO', 'TOTAL', ' CPC', 'GRUPO ', 'PARTIDA', 'PAC/NO PAC',
    'Fuente de Financiamiento', 'Observaciones')
ENCABEZADOS_CLASIFICADOS = (*ENCABEZADOS_CONSOLIDADO[:10], *ENCABEZADOS_CONSOLIDADO[11:])
ENCABEZADOS_PROGRAMACION = ('ÁREA', 'MOTIVO', 'EQUIPOS ACTUALES RELACIONADOS', 'BIEN O SERVICIO',
    'CANTIDAD', 'V. UNITARIO', 'TOTAL', 'SEMESTRE', 'MES', 'JUSTIFICACIÓN')
ENCABEZADOS_PROGRAMACION_CLASES = (*ENCABEZADOS_PROGRAMACION, 'CLASE DE BIEN O SERVICIO')
ENCABEZADOS_FASES = ('PROYECTO O CONJUNTO', 'FASE', 'RESULTADO VERIFICABLE DE LA FASE',
    'CONDICIÓN PARA LA SIGUIENTE FASE')
_CLAVES = tuple(c[0] for c in COLUMNAS_PAC)


def clases_bien_de(contenido):
    """Las copias emitidas conservan las etiquetas de su captura original."""
    return CLASES_BIEN if contenido.get('matriz_detalle_version') == 1 else CLASES_BIEN_LEGADO


def _texto(valor):
    return str(valor if valor is not None else '').strip()


def centro_costo_de(unidad):
    dependencia = getattr(unidad, 'adscrita_a', None) if unidad is not None else None
    return _texto(getattr(dependencia, 'centro_costo', '')) if dependencia and dependencia.activa else ''


def _uuid(valor):
    try:
        return str(UUID(str(valor)))
    except (ValueError, TypeError, AttributeError):
        return ''


def _clasificacion(valor):
    texto = _texto(valor)
    return {'PAC': 'pac', 'NO PAC': 'no_pac', 'NO_PAC': 'no_pac', 'NOPAC': 'no_pac',
            'POR DEFINIR': 'por_definir'}.get(texto.upper(), texto)


def _significativa(fila):
    if not isinstance(fila, dict):
        return True
    for clave, valor in fila.items():
        if clave in ('id_necesidad', 'grupo', 'semestre', 'area_nombre', 'equipo_referencia', 'sustento_uso'):
            continue
        if clave == 'equipos_referencia' and valor in (None, '', '[]', []):
            continue
        if clave == 'clasificacion_pac' and _clasificacion(valor) in ('', 'por_definir'):
            continue
        if clave == 'categoria' and _texto(valor) in ('', 'equipos'):
            continue
        if _texto(valor):
            return True
    return False


def _mes(valor):
    texto = _texto(valor)
    return int(texto) if not isinstance(valor, bool) and texto.isdecimal() and 1 <= int(texto) <= 12 else None


def semestre_compra(valor):
    mes = _mes(valor)
    return (1 if mes <= 6 else 2) if mes else None


def _fase(valor):
    texto = _texto(valor)
    return int(texto) if not isinstance(valor, bool) and texto.isdecimal() and 1 <= int(texto) <= 20 else None


def _pares_fase(fila):
    """La agrupación describe una compra; nunca añade cantidades o importes."""
    if not _texto(fila.get('grupo_fases')):
        return []
    pares = [('Proyecto o conjunto de compras', _texto(fila.get('grupo_fases'))),
             ('Fase', str(_fase(fila.get('fase_numero'))) if _fase(fila.get('fase_numero')) else 'Por completar'),
             ('Resultado verificable de la fase', strip_tags(_texto(fila.get('resultado_fase'))))]
    if _texto(fila.get('condicion_siguiente_fase')):
        pares.append(('Condición para la siguiente fase', strip_tags(_texto(fila['condicion_siguiente_fase']))))
    return pares


def opciones_unidad_pac(unidad):
    """Áreas actuales y activos propios; una baja puede motivar su reposición."""
    areas = {'unidad': 'Toda la unidad'}
    equipos = {}
    identidades = {}
    if unidad is not None and getattr(unidad, 'pk', None):
        from django.db.models import Q
        from apps.gestion_unidades.models.espacios import EspacioReservable
        from apps.recursos.models.unidades import UnidadEquipo
        areas.update((str(e.pk), e.nombre) for e in EspacioReservable.objects.filter(
            unidad=unidad, activo=True).order_by('orden', 'nombre', 'pk'))
        for equipo in UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad)).select_related(
                'equipo').distinct().order_by('codigo_unidad', 'pk'):
            nombre = f'{equipo.codigo_unidad} · {equipo.equipo.nombre}'
            if equipo.fecha_baja:
                nombre += ' (dado de baja)'
            equipos[str(equipo.pk)] = nombre
            identidades[str(equipo.pk)] = dict(nombre=equipo.equipo.nombre, codigo=equipo.codigo_unidad)
    if len(areas) == 1:
        areas['unidad'] = 'Unidad completa'
    return dict(areas=areas, equipos=equipos, identidades_equipos=identidades)


def _equipos_ids(valor):
    if valor in (None, ''):
        return []
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except (TypeError, ValueError) as error:
            raise ValidationError('Selecciona los equipos relacionados desde la lista de esta unidad.') from error
    if not isinstance(valor, list) or any(isinstance(v, bool) or not str(v).isdecimal() or int(v) <= 0 for v in valor):
        raise ValidationError('La selección de equipos relacionados no tiene una estructura válida.')
    return list(dict.fromkeys(str(int(v)) for v in valor))


def _nombre_comprobado(fila, identidades):
    """Corrige exclusivamente nombres generados para un activo propio vinculado.

    Las características, prefijos escritos por la unidad y códigos sin vínculo
    comprobable permanecen íntegros. No se usa al leer una copia emitida.
    """
    try:
        referencias = _equipos_ids(fila.get('equipos_referencia'))
    except ValidationError:
        return fila.get('item', '')
    actual = _texto(fila.get('item'))
    for referencia in referencias:
        identidad = identidades.get(referencia)
        if not identidad:
            continue
        nombre, codigo = identidad['nombre'], identidad['codigo']
        if nombre and codigo and actual in {
                f'{nombre} ({codigo})', f'{nombre} · {codigo}', f'{nombre} ({codigo}) · {codigo}'}:
            return nombre
    return fila.get('item', '')


def preparar_pac(contenido, *, unidad=None):
    """Proyección editable sin guardar: conserva datos anteriores y añade IDs."""
    from .catalogo_cpc import fijar_referencia_cpc
    resultado = deepcopy(contenido) if isinstance(contenido, dict) else {}
    resultado['pac_version'] = PAC_VERSION
    # Este marcador amplía los borradores, sin reinterpretar documentos v2
    # ya emitidos que conservan la estructura anterior.
    resultado['clases_bien_version'] = 1
    resultado['inversion_gestion_version'] = 1
    resultado['matriz_detalle_version'] = 1
    resultado['compras_resumen_version'] = 1
    resultado['estado_equipos_informe_version'] = 1
    resultado.setdefault('centro_costo', '')
    if centro_costo_de(unidad):
        resultado['centro_costo'] = centro_costo_de(unidad)
    filas = resultado.get('compras', [])
    if not isinstance(filas, list):
        return resultado  # La validación informa la estructura inválida.
    con_referencias = any(isinstance(fila, dict) and fila.get('equipos_referencia') not in (None, '', '[]', [])
                         for fila in filas)
    identidades = opciones_unidad_pac(unidad)['identidades_equipos'] if unidad is not None and con_referencias else {}
    preparados, usados = [], set()
    for posicion, original in enumerate(filas):
        if not _significativa(original):
            continue
        if not isinstance(original, dict):
            preparados.append(original)
            continue
        fila = dict(original)
        fila['item'] = _nombre_comprobado(fila, identidades)
        identificador = _uuid(fila.get('id_necesidad'))
        if not identificador or identificador in usados:
            # Un GET no guarda redacciones. La primera proyección de una
            # fila antigua debe conservar el mismo ID al recibir su POST.
            base = {k: v for k, v in fila.items() if k not in ('id_necesidad', 'grupo')}
            referencia = json.dumps([posicion, base], sort_keys=True, ensure_ascii=True, default=str)
            identificador = str(uuid5(NAMESPACE_URL, 'citt:necesidad-anual:v1:' + referencia))
        usados.add(identificador)
        fila['id_necesidad'] = identificador
        fila['clasificacion_pac'] = _clasificacion(fila.get('clasificacion_pac')) or 'por_definir'
        # El trimestre histórico no fija un mes exacto: la programación nueva
        # queda pendiente hasta que la unidad la revise expresamente.
        fila.setdefault('area_id', '')
        fila.setdefault('tipo_necesidad', '')
        fila.setdefault('clase_bien', '')
        fila.setdefault('especificaciones', '')
        fila.setdefault('unidad_medida', '')
        fila.setdefault('mes_compra', '')
        fila.setdefault('equipos_referencia', [])
        for clave in ('grupo_fases', 'fase_numero', 'resultado_fase', 'condicion_siguiente_fase'):
            fila.setdefault(clave, '')
        fila['semestre'] = semestre_compra(fila.get('mes_compra'))
        preparados.append(fijar_referencia_cpc(fila))
    resultado['compras'] = preparados
    return resultado


def _filas_formulario(post):
    nombres = ('id_necesidad', *_CLAVES)
    columnas = [post.getlist(f'compras__{clave}') for clave in nombres]
    return [{clave: _texto(valor) for clave, valor in zip(nombres, valores)}
            for valores in zip_longest(*columnas, fillvalue='')]


def leer_pac(post, anterior, *, unidad=None):
    """Lee sólo filas significativas; una nueva necesidad recibe UUID del servidor.

    Un ID recibido sólo se conserva si ya pertenece a la redacción anterior de
    este documento. Los campos internos antiguos omitidos por la nueva interfaz
    se conservan por ese ID, sin convertirlos en códigos universitarios.
    """
    from .catalogo_cpc import fijar_referencia_cpc
    anterior = preparar_pac(anterior, unidad=unidad)
    opciones = opciones_unidad_pac(unidad)
    previas = {str(f['id_necesidad']): f for f in anterior.get('compras', [])
               if isinstance(f, dict) and _uuid(f.get('id_necesidad'))} if isinstance(anterior.get('compras', []), list) else {}
    filas, usados = [], set()
    for enviada in _filas_formulario(post):
        if not _significativa(enviada):
            continue
        identificador = enviada['id_necesidad']
        if identificador and (identificador not in previas or identificador in usados):
            raise ValidationError('La necesidad cambió o pertenece a otro documento. Abre el plan actual antes de guardar.')
        previa = previas.get(identificador, {})
        fila = deepcopy(previa)
        fila.update({clave: (enviada[clave] if f'compras__{clave}' in post else deepcopy(previa.get(clave, '')))
                     for clave in _CLAVES})
        fila['id_necesidad'] = identificador or str(uuid4())
        fila['clasificacion_pac'] = _clasificacion(fila.get('clasificacion_pac')) or 'por_definir'
        area = _texto(fila.get('area_id'))
        equipos = _equipos_ids(fila.get('equipos_referencia'))
        if area and area not in opciones['areas']:
            raise ValidationError('El área seleccionada no está activa o pertenece a otra unidad.')
        if equipos and (unidad is None or any(e not in opciones['equipos'] for e in equipos)):
            raise ValidationError('Selecciona sólo equipos registrados en esta unidad.')
        fila['area_id'] = area
        fila['area_nombre'] = opciones['areas'].get(area, '')
        fila['equipos_referencia'] = equipos
        fila['item'] = _nombre_comprobado(fila, opciones['identidades_equipos'])
        fila['equipo_referencia'] = '; '.join(opciones['equipos'][e] for e in equipos)
        fila['mes_compra'] = str(_mes(fila.get('mes_compra'))) if _mes(fila.get('mes_compra')) else _texto(fila.get('mes_compra'))
        fila['semestre'] = semestre_compra(fila.get('mes_compra'))
        usados.add(fila['id_necesidad'])
        filas.append(fijar_referencia_cpc(fila))
    return dict(pac_version=PAC_VERSION, clases_bien_version=1, inversion_gestion_version=1, matriz_detalle_version=1,
                compras_resumen_version=1, estado_equipos_informe_version=1,
                centro_costo=centro_costo_de(unidad) or _texto(post.get('centro_costo', anterior.get('centro_costo', ''))), compras=filas)


def identidades_formulario_pac(post, contenido):
    """IDs de respuesta alineados con todas las filas DOM, incluida la vacía.

    Se llama con el contenido que acaba de guardar ``leer_pac``. Permite que
    el navegador conserve los UUID nuevos del servidor durante el autosave.
    """
    filas = contenido.get('compras', []) if isinstance(contenido, dict) else []
    identidades = iter(f.get('id_necesidad', '') for f in filas if isinstance(f, dict) and _significativa(f))
    return [next(identidades, '') if _significativa(fila) else '' for fila in _filas_formulario(post)]


def validar_pac(contenido, unidad=None):
    """Hallazgos puros; los códigos desconocidos requieren revisión, no invención."""
    if not isinstance(contenido, dict) or contenido.get('pac_version') not in VERSIONES_PAC:
        return []
    hallazgos = []
    opciones = opciones_unidad_pac(unidad) if unidad is not None and contenido.get('pac_version') == PAC_VERSION else None
    def falta(regla, mensaje, severidad='bloqueo'):
        hallazgos.append(dict(regla=regla, mensaje=mensaje, severidad=severidad))
    filas = contenido.get('compras', [])
    if not isinstance(filas, list):
        falta('pac_estructura_invalida', 'Necesidades anuales: la tabla debe contener una lista de filas.')
        return hallazgos
    centro = contenido.get('centro_costo', '')
    if not isinstance(centro, str):
        falta('pac_centro_invalido', 'El centro de costo debe ser texto.')
    ids, significativas, fases = set(), [], {}
    for posicion, fila in enumerate(filas, 1):
        if not isinstance(fila, dict):
            falta('pac_estructura_invalida', f'Necesidad {posicion}: la fila no tiene una estructura válida.')
            continue
        if not _significativa(fila):
            continue
        significativas.append(fila)
        identificador = _uuid(fila.get('id_necesidad'))
        if not identificador or identificador in ids:
            falta('pac_identidad_invalida', f'Necesidad {posicion}: guarda el plan desde el editor para conservar un identificador único.')
        ids.add(identificador)
        for clave in _CLAVES:
            if clave == 'equipos_referencia':
                continue
            valor = fila.get(clave)
            if valor is not None and not isinstance(valor, (str, int, float, Decimal)) or isinstance(valor, bool):
                falta('pac_dato_invalido', f'Necesidad {posicion}: el campo {clave} no tiene un valor simple válido.')
        if _clasificacion(fila.get('clasificacion_pac')) not in ('', 'por_definir', 'pac', 'no_pac'):
            falta('pac_clasificacion_invalida', f'Necesidad {posicion}: selecciona PAC, NO PAC o Por definir.')
        if contenido.get('pac_version') >= 2:
            area = _texto(fila.get('area_id'))
            if not area or area != 'unidad' and (not area.isdecimal() or int(area) <= 0):
                falta('pac_area_pendiente', f'Necesidad {posicion}: selecciona el área de destino o Toda la unidad.')
            elif opciones is not None and area not in opciones['areas']:
                falta('pac_area_ajena', f'Necesidad {posicion}: el área seleccionada no está activa en esta unidad; revisa la selección.')
            if _texto(fila.get('tipo_necesidad')) not in dict(TIPOS_NECESIDAD):
                falta('pac_tipo_pendiente', f'Necesidad {posicion}: selecciona el motivo de la adquisición.')
            if contenido.get('clases_bien_version') == 1 and _texto(fila.get('clase_bien')) not in dict(clases_bien_de(contenido)):
                falta('pac_clase_pendiente', f'Necesidad {posicion}: selecciona equipos, software y licencias, materiales, insumos, reactivos, repuestos y accesorios o servicios de soporte.')
            if contenido.get('matriz_detalle_version') == 1:
                nombre = _texto(fila.get('item'))
                if '\n' in nombre or '\r' in nombre or len(nombre) > 300:
                    falta('pac_nombre_extenso', f'Necesidad {posicion}: deja sólo el nombre del bien o servicio (hasta 300 caracteres). Registra las características en Especificaciones y las razones de compra en Justificación.')
            if contenido.get('compras_resumen_version') == 1:
                from .catalogo_cpc import validar_codigo_cpc
                error_cpc = validar_codigo_cpc(fila.get('cpc', ''))
                if error_cpc:
                    falta('pac_cpc_invalido', f'Necesidad {posicion}: {error_cpc}')
            if not _mes(fila.get('mes_compra')):
                falta('pac_programacion_pendiente', f'Necesidad {posicion}: selecciona el mes previsto de adquisición; el semestre se calcula automáticamente.')
            try:
                equipos = _equipos_ids(fila.get('equipos_referencia'))
                if opciones is not None and any(e not in opciones['equipos'] for e in equipos):
                    falta('pac_equipo_ajeno', f'Necesidad {posicion}: revisa los equipos actuales; alguno no pertenece a esta unidad.')
                reposicion_fisica = (contenido.get('clases_bien_version') != 1
                                     or _texto(fila.get('clase_bien')) in ('', 'equipos'))
                if fila.get('tipo_necesidad') == 'reposicion' and reposicion_fisica and not equipos:
                    falta('pac_reposicion_sin_equipo', f'Necesidad {posicion}: identifica al menos un equipo actual que se prevé reemplazar.')
            except ValidationError as error:
                falta('pac_equipos_invalidos', f'Necesidad {posicion}: ' + ' '.join(error.messages))
        pendientes = [etiqueta for clave, etiqueta in (('cpc', 'CPC'), ('partida', 'partida presupuestaria'),
            ('fuente_pac', 'fuente de financiamiento universitaria')) if not _texto(fila.get(clave))]
        if _clasificacion(fila.get('clasificacion_pac')) in ('', 'por_definir'):
            pendientes.append('clasificación PAC/NO PAC')
        if pendientes:
            falta('pac_transferencia_pendiente', f'Necesidad {posicion}: por revisar para la transferencia universitaria: '
                  + ', '.join(pendientes) + '. No impide presentar el requerimiento.', 'revision')
        if contenido.get('inversion_gestion_version') == 1:
            grupo = _texto(fila.get('grupo_fases'))
            numero = _fase(fila.get('fase_numero'))
            if grupo:
                if not numero:
                    falta('pac_fase_numero_pendiente', f'Necesidad {posicion}: indica el número de fase entre 1 y 20.')
                if not strip_tags(_texto(fila.get('resultado_fase'))).strip():
                    falta('pac_fase_resultado_pendiente', f'Necesidad {posicion}: indica qué resultado verificable permitirá esta fase.')
                if numero and _mes(fila.get('mes_compra')):
                    grupo_normal = ' '.join(grupo.casefold().split())
                    fases.setdefault(grupo_normal, {}).setdefault(numero, []).append(_mes(fila['mes_compra']))
            elif any(_texto(fila.get(clave)) for clave in ('fase_numero', 'resultado_fase', 'condicion_siguiente_fase')):
                falta('pac_fase_sin_grupo', f'Necesidad {posicion}: identifica el proyecto o conjunto de compras por fases, o elimina sus datos de fase para registrar una adquisición única.')
    for grupo, etapas in fases.items():
        numeros = sorted(etapas)
        for anterior, siguiente in zip(numeros, numeros[1:]):
            if max(etapas[anterior]) > min(etapas[siguiente]):
                falta('pac_fases_orden_invalido', f'Compras por fases «{grupo}»: el mes de la fase {siguiente} no puede preceder a una compra de la fase {anterior}; revisa su programación.')
                break
    if significativas and not _texto(centro):
        falta('pac_centro_pendiente', 'Centro de costo agrupador por revisar para la transferencia universitaria.', 'revision')
    return hallazgos


def _numero(valor):
    if isinstance(valor, bool) or isinstance(valor, (dict, list, tuple)):
        return None
    try:
        numero = Decimal(_texto(valor).replace(',', '.'))
        return numero if numero.is_finite() and numero >= 0 and numero <= Decimal('1e12') else None
    except (DecimalException, TypeError, ValueError):
        return None


def datos_editor_pac(contenido, unidad=None, diagnostico=None):
    from .compras_resumen import resumen_compras
    opciones = opciones_unidad_pac(unidad)
    clases_bien = isinstance(contenido, dict) and contenido.get('clases_bien_version') == 1
    gestion_inversion = isinstance(contenido, dict) and contenido.get('inversion_gestion_version') == 1
    detalle_matriz = isinstance(contenido, dict) and contenido.get('matriz_detalle_version') == 1
    resumen_por_clase = isinstance(contenido, dict) and contenido.get('compras_resumen_version') == 1
    def campo(clave, etiqueta, tipo='texto', opciones=(), ayuda=''):
        return dict(clave=clave, etiqueta=etiqueta, tipo=tipo, opciones=opciones, ayuda=ayuda,
                    requerido=clave in ('area_id', 'tipo_necesidad', 'item', 'cantidad', 'costo_unitario', 'justificacion', 'mes_compra')
                    or clave == 'clase_bien' and clases_bien)
    grupos = [dict(clave='necesidad', etiqueta='Bien o servicio y sustento', campos=[
        campo('area_id', 'Área de destino', 'opcion', tuple(opciones['areas'].items())),
        campo('tipo_necesidad', 'Motivo', 'opcion', TIPOS_NECESIDAD),
        campo('clase_bien', 'Clase de bien o servicio', 'opcion', clases_bien_de(contenido) if isinstance(contenido, dict) else CLASES_BIEN,
              ayuda='Selecciona qué se requiere comprar. El motivo indica por qué hace falta; la clase identifica qué se adquirirá.'),
        campo('item', 'Nombre del bien o servicio', ayuda='Sólo el nombre: Computador de escritorio, Licencia CAD o Filamento PLA. El área, motivo, código de inventario y características se registran por separado.'),
        campo('especificaciones', 'Especificaciones del bien o servicio', 'multilinea',
              ayuda='Características necesarias sin justificar la compra. Ej.: memoria y almacenamiento; vigencia y número de usuarios de la licencia; dimensiones, concentración, presentación o compatibilidad del repuesto.'),
        campo('unidad_medida', 'Unidad de medida o presentación',
              ayuda='Ej.: unidad, licencia anual, usuario/mes, kilogramo, litro, caja de 100 unidades. La cantidad corresponde a esta presentación.'),
        campo('cantidad', 'Cantidad', 'numero'),
        campo('costo_unitario', 'Valor unitario (USD)', 'numero'),
        campo('mes_compra', 'Mes de adquisición', 'opcion', MESES_COMPRA),
        campo('equipos_referencia', 'Equipos actuales relacionados'),
        campo('justificacion', 'Justificación de la necesidad', 'multilinea',
              ayuda='Indica qué existe y qué falta o falla, qué uso o diagnóstico lo respalda y qué mejora permitirá. En una reposición, explica qué se sustituye o actualiza; en una ampliación, compara la capacidad actual con la requerida.')]),
        dict(clave='transferencia', etiqueta='Clasificación administrativa (opcional)', campos=[
        campo('cpc', 'CPC', ayuda='Código del bien o servicio que se requiere adquirir; confirma su clasificación. No corresponde copiar el código de inventario del equipo que se reemplaza.'), campo('partida', 'Partida presupuestaria'), campo('grupo', 'Grupo de gasto'),
        campo('clasificacion_pac', 'Clasificación PAC / NO PAC', 'opcion', CLASIFICACIONES_PAC),
        campo('fuente_pac', 'Fuente de financiamiento universitaria', ayuda='Código o denominación confirmado por el área administrativa; no equivale a la fuente interna.'),
        campo('observaciones', 'Observaciones', 'multilinea')])]
    if gestion_inversion:
        grupos.append(dict(clave='fases', etiqueta='Adquisición por fases (opcional)', campos=[
            campo('grupo_fases', 'Proyecto o conjunto de compras',
                  ayuda='Déjalo vacío si la adquisición no se divide en fases. Usa el mismo nombre para todas las compras del proyecto; por ejemplo, Renovación del área de cómputo.'),
            campo('fase_numero', 'Número de fase', 'entero',
                  ayuda='Del 1 al 20. Una fase puede incluir varios bienes. Si empezó en otro año, conserva su número; no repitas las cantidades ya compradas.'),
            campo('resultado_fase', 'Resultado verificable de esta fase', 'multilinea',
                  ayuda='Ejemplo: habilitar 10 puestos para las prácticas previstas, con registro de uso y responsable asignado.'),
            campo('condicion_siguiente_fase', 'Qué debe cumplirse antes de la siguiente fase', 'multilinea',
                  ayuda='Opcional. Ejemplo: verificar la utilización de los puestos instalados y la disponibilidad de presupuesto. Las compras de otros años se registran en su plan anual correspondiente.')]))
    filas, total, importes_completos = [], Decimal(0), True
    for fila in contenido.get('compras', []) if isinstance(contenido, dict) and isinstance(contenido.get('compras', []), list) else []:
        if not isinstance(fila, dict) or not _significativa(fila):
            continue
        cantidad, costo = _numero(fila.get('cantidad')), _numero(fila.get('costo_unitario'))
        subtotal = cantidad * costo if cantidad is not None and cantidad > 0 and costo is not None else None
        importes_completos = importes_completos and subtotal is not None
        total += subtotal or 0
        try:
            equipos = _equipos_ids(fila.get('equipos_referencia'))
        except ValidationError:
            equipos = []  # El validador señala el dato inválido; el GET no lo altera.
        valor = dict(fila, grupo=_texto(fila.get('partida'))[:2], semestre=semestre_compra(fila.get('mes_compra')))
        filas.append(dict(valor=valor, total=subtotal, equipos_ids=equipos,
                          equipos_json=json.dumps(equipos), semestre=valor['semestre']))
    # Sin necesidades, la suma vacía es cero. Con importes pendientes no se
    # presenta la suma de unas pocas filas como total de todo el requerimiento.
    resumen = resumen_compras(contenido) if resumen_por_clase else None
    datos = dict(grupos_pac=grupos, filas_pac=filas, pac_total=resumen['total_general'] if resumen is not None else total if importes_completos else None,
                version_pac=contenido.get('pac_version') if isinstance(contenido, dict) else None,
                clases_bien_version=1 if clases_bien else None,
                inversion_gestion_version=1 if gestion_inversion else None,
                matriz_detalle_version=1 if detalle_matriz else None,
                compras_resumen_version=1 if resumen_por_clase else None,
                resumen_compras=resumen,
                centro_costo=contenido.get('centro_costo', '') if isinstance(contenido, dict) else '',
                centro_costo_automatico=bool(centro_costo_de(unidad)),
                grupos_fases=tuple(dict.fromkeys(_texto(f['valor'].get('grupo_fases')) for f in filas
                                                if _texto(f['valor'].get('grupo_fases')))) if gestion_inversion else (),
                fuentes_pac=FUENTES_REFERENCIA,
                campos_pac={c['clave']: c for grupo in grupos for c in grupo['campos']},
                opciones_areas=tuple(opciones['areas'].items()), opciones_equipos=tuple(opciones['equipos'].items()))
    if isinstance(diagnostico, dict) and diagnostico:
        from .compras_contraste import contrastar_compras
        # El GET ya obtuvo esta lectura: el contraste no vuelve a consultar
        # inventario, mantenimiento ni uso de cada necesidad.
        datos['contraste_pac'] = contrastar_compras(contenido, diagnostico)
    return datos


def bloques_pac(contenido):
    """Una tabla económica legible y la clasificación detallada por necesidad."""
    if isinstance(contenido, dict) and contenido.get('compras_resumen_version') == 1:
        from .compras_resumen import bloques_resumen_compras
        return bloques_resumen_compras(contenido)
    datos = datos_editor_pac(contenido)
    if not datos['filas_pac']:
        return [dict(tipo='vacio', titulo='Necesidades de bienes y servicios', texto='Sin adquisiciones registradas para el año siguiente.')]
    resumen, detalles = [], []
    etiquetas = dict(CLASIFICACIONES_PAC)
    nueva = contenido.get('pac_version') == PAC_VERSION
    for indice, fila in enumerate(datos['filas_pac'], 1):
        valor = fila['valor']
        importe = f"{fila['total']:,.2f}" if fila['total'] is not None else 'Por completar'
        economica = [_texto(valor.get('item')), _texto(valor.get('cantidad')), _texto(valor.get('costo_unitario')), importe]
        mes = _mes(valor.get('mes_compra'))
        resumen.append([_texto(valor.get('area_nombre')) or 'Por confirmar', *economica,
                        dict(MESES_COMPRA).get(str(mes), 'Por confirmar'),
                        str(fila['semestre']) if fila['semestre'] else 'Por confirmar'] if nueva else economica)
        pares = [('Justificación', strip_tags(_texto(valor.get('justificacion'))))]
        if nueva:
            # Área e importe y mes ya están en el resumen. El sustento sólo
            # añade motivo, referencias reales y clasificaciones conocidas.
            pares.insert(0, ('Motivo', dict(TIPOS_NECESIDAD).get(valor.get('tipo_necesidad'), 'Por confirmar')))
            if contenido.get('clases_bien_version') == 1:
                pares.insert(0, ('Clase de bien o servicio', dict(clases_bien_de(contenido)).get(valor.get('clase_bien'), 'Por confirmar')))
            if contenido.get('matriz_detalle_version') == 1:
                pares.extend((etiqueta, _texto(valor.get(clave))) for clave, etiqueta in (
                    ('especificaciones', 'Especificaciones'), ('unidad_medida', 'Unidad de medida o presentación'))
                    if _texto(valor.get(clave)))
            if _texto(valor.get('equipo_referencia')):
                pares.insert(1, ('Equipos actuales relacionados', _texto(valor['equipo_referencia'])))
            if contenido.get('inversion_gestion_version') == 1:
                pares.extend(_pares_fase(valor))
            pares.extend((etiqueta, _texto(valor.get(clave))) for clave, etiqueta in (
                ('cpc', 'CPC'), ('partida', 'Partida presupuestaria'), ('fuente_pac', 'Fuente universitaria'),
                ('observaciones', 'Observaciones')) if _texto(valor.get(clave)))
            if _clasificacion(valor.get('clasificacion_pac')) in ('pac', 'no_pac'):
                pares.append(('Clasificación', etiquetas[_clasificacion(valor['clasificacion_pac'])]))
        else:
            pares.extend([
            ('CPC', _texto(valor.get('cpc')) or 'Por definir'),
            ('Partida presupuestaria', _texto(valor.get('partida')) or 'Por definir'),
            ('Grupo de gasto', valor['grupo'] or 'Por definir'),
            ('Clasificación', etiquetas.get(_clasificacion(valor.get('clasificacion_pac')), 'Por definir')),
            ('Fuente universitaria', _texto(valor.get('fuente_pac')) or 'Por definir'),
            ('Observaciones', _texto(valor.get('observaciones')) or 'Sin observaciones adicionales')])
        detalles.append(dict(tipo='pares', titulo=f"Necesidad {indice}: {_texto(valor.get('item'))}", pares=pares))
    total = f"{datos['pac_total']:,.2f}" if datos['pac_total'] is not None else 'Por completar'
    resumen.append(['Total previsto', '', '', '', total, '', ''] if nueva else ['Total previsto', '', '', total])
    return [dict(tipo='tabla', titulo='Necesidades de bienes y servicios',
                 conservar_total=contenido.get('inversion_gestion_version') == 1,
                 cabecera=['Área', 'Bien o servicio', 'Cantidad', 'Valor unitario (USD)', 'Total (USD)', 'Mes', 'Semestre']
                 if nueva else ['Bien o servicio', 'Cantidad', 'Valor unitario (USD)', 'Total (USD)'], filas=resumen), *detalles]


def observaciones_pac(fila, *, incluir_clase=False, incluir_fases=False, incluir_detalle=False):
    """La matriz no tiene otra columna para el sustento de la necesidad."""
    justificacion = ' '.join(unescape(strip_tags(_texto(fila.get('justificacion')))).split())
    observaciones = _texto(fila.get('observaciones'))
    partes = []
    if incluir_clase:
        catalogo = CLASES_BIEN if incluir_detalle else CLASES_BIEN_LEGADO
        partes.append('Clase: ' + dict(catalogo).get(fila.get('clase_bien'), 'Por confirmar'))
    if incluir_detalle:
        for clave, etiqueta in (('especificaciones', 'Especificaciones'), ('unidad_medida', 'Unidad de medida')):
            if _texto(fila.get(clave)):
                partes.append(etiqueta + ': ' + _texto(fila[clave]))
    if _texto(fila.get('area_nombre')):
        partes.append('Área: ' + _texto(fila['area_nombre']))
    if fila.get('tipo_necesidad') in dict(TIPOS_NECESIDAD):
        partes.append('Motivo: ' + dict(TIPOS_NECESIDAD)[fila['tipo_necesidad']])
    if _texto(fila.get('equipo_referencia')):
        partes.append('Equipos actuales: ' + _texto(fila['equipo_referencia']))
    mes = _mes(fila.get('mes_compra'))
    if mes:
        partes.append(f'Programación: {dict(MESES_COMPRA)[str(mes)]} · semestre {semestre_compra(mes)}')
    if incluir_fases:
        partes.extend(etiqueta + ': ' + valor for etiqueta, valor in _pares_fase(fila) if valor)
    if justificacion:
        partes.append('Justificación: ' + justificacion)
    comparable = ' '.join(unescape(strip_tags(observaciones)).split()).casefold()
    if observaciones and comparable not in (justificacion.casefold(), ('Justificación: ' + justificacion).casefold()):
        partes.append(('Observaciones: ' if partes else '') + observaciones)
    return '\n'.join(partes)


def render_pac_xlsx(contenido, unidad_nombre, anio_planificado, *, borrador=True):
    """Libro nuevo; sólo exporta estas necesidades, nunca datos de la referencia."""
    if isinstance(contenido, dict) and contenido.get('compras_resumen_version') == 1:
        from .compras_resumen import render_resumen_compras_xlsx
        return render_resumen_compras_xlsx(contenido, unidad_nombre, anio_planificado, borrador=borrador)
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.workbook.properties import CalcProperties
    from openpyxl.utils import get_column_letter

    contenido = contenido if isinstance(contenido, dict) else {}
    filas = contenido.get('compras', [])
    filas = [f for f in filas if isinstance(f, dict) and _significativa(f)] if isinstance(filas, list) else []
    libro = Workbook()
    libro.remove(libro.active)
    libro.calculation = CalcProperties(calcId=191029, fullCalcOnLoad=True, forceFullCalc=True)
    libro.properties.title = f'Requerimientos de bienes y servicios {anio_planificado}'
    libro.properties.subject = 'Requerimientos por revisar; no constituye un PAC aprobado ni autoriza gastos.'
    verde, gris = '27613B', 'D9E3DD'
    borde = Border(*( [Side(style='thin', color=gris)] * 4))
    def texto(celda, valor):
        celda.value = _texto(valor)
        celda.data_type = 's'  # Los datos de usuario nunca se convierten en fórmulas.
        celda.quotePrefix = celda.value.lstrip().startswith(('=', '+', '-', '@'))
    for nombre, seleccion in (('CONSOLIDADO', None), ('PAC', 'pac'), ('NO PAC', 'no_pac')):
        hoja = libro.create_sheet(nombre)
        cabecera = ENCABEZADOS_CONSOLIDADO if seleccion is None else ENCABEZADOS_CLASIFICADOS
        ultima = len(cabecera)
        for numero, titulo in ((1, 'UNIVERSIDAD POLITÉCNICA ESTATAL DEL CARCHI'),
            (2, f'REQUERIMIENTOS POR CENTRO DE COSTO PARA EL EJERCICIO ECONÓMICO {anio_planificado}'),
            (3, f'PROFORMA PRESUPUESTARIA {anio_planificado} · ' + ('BORRADOR' if borrador else 'REQUERIMIENTOS REGISTRADOS'))):
            hoja.merge_cells(start_row=numero, start_column=1, end_row=numero, end_column=ultima)
            texto(hoja.cell(numero, 1), titulo)
            hoja.cell(numero, 1).font = Font(name='Arial', size=11, bold=True, color=verde)
            hoja.cell(numero, 1).alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        hoja['A3'].comment = Comment('No constituye PAC aprobado ni autorización de gasto. Las hojas PAC y NO PAC '
            'incluyen sólo clasificaciones expresamente registradas; lo no clasificado permanece en CONSOLIDADO. '
            'CPC, partida, fuente y centro agrupador pendientes deben revisarse con el área administrativa.', 'Sistema de unidades')
        for columna, etiqueta in enumerate(cabecera, 1):
            celda = hoja.cell(4, columna)
            celda.value, celda.data_type = etiqueta, 's'
            celda.font = Font(name='Arial', size=10, bold=True, color='FFFFFF')
            celda.fill = PatternFill('solid', fgColor=verde)
            celda.alignment = Alignment(wrap_text=True, vertical='center')
            celda.border = borde
        anchos = [7, 29, 29, 62, 13, 17, 19, 19, 10, 17, 17, 25, 40]
        if seleccion is not None:
            anchos.pop(10)
        fila_excel, importes_pendientes = 5, 0
        for indice, fila in enumerate(filas, 1):
            clasificacion = _clasificacion(fila.get('clasificacion_pac'))
            if seleccion and clasificacion != seleccion:
                continue
            valores = [indice, unidad_nombre, contenido.get('centro_costo', ''), fila.get('item', ''),
                _numero(fila.get('cantidad')), _numero(fila.get('costo_unitario')), None, fila.get('cpc', ''),
                None, fila.get('partida', '')]
            if seleccion is None:
                valores.append({'pac': 'PAC', 'no_pac': 'NOPAC'}.get(clasificacion, ''))
            valores.extend([fila.get('fuente_pac', ''), observaciones_pac(fila,
                incluir_clase=contenido.get('clases_bien_version') == 1,
                incluir_fases=contenido.get('inversion_gestion_version') == 1,
                incluir_detalle=contenido.get('matriz_detalle_version') == 1)])
            for columna, valor in enumerate(valores, 1):
                celda = hoja.cell(fila_excel, columna)
                if columna in (1, 5, 6):
                    celda.value = valor
                    celda.number_format = '0.###' if columna == 5 else '#,##0.00' if columna == 6 else '0'
                elif columna not in (7, 9):
                    texto(celda, valor)
                    if columna in (8, 10) or columna == (12 if seleccion is None else 11):
                        celda.number_format = '@'
                celda.font = Font(name='Arial', size=10)
                celda.alignment = Alignment(vertical='top', wrap_text=True)
                celda.border = borde
            importe_completo = valores[4] is not None and valores[4] > 0 and valores[5] is not None
            if importe_completo:
                hoja.cell(fila_excel, 7, f'=E{fila_excel}*F{fila_excel}').number_format = '#,##0.00'
            else:
                importes_pendientes += 1
                aviso = 'Completa una cantidad positiva y un valor unitario no negativo para calcular este importe.'
                hoja.cell(fila_excel, 7).comment = Comment(aviso, 'Sistema de unidades')
                for columna, pendiente in ((5, valores[4] is None or valores[4] <= 0), (6, valores[5] is None)):
                    if pendiente:
                        hoja.cell(fila_excel, columna).fill = PatternFill('solid', fgColor='FFF2CC')
                        hoja.cell(fila_excel, columna).comment = Comment(aviso, 'Sistema de unidades')
            hoja.cell(fila_excel, 9, f'=IF(J{fila_excel}="","",LEFT(J{fila_excel},2))')
            lineas = max(sum(max(1, ceil(len(parte) / max(8, ancho - 2)))
                             for parte in _texto(valor).split('\n')) for valor, ancho in zip(valores, anchos))
            # Excel conserva todo el contenido de la celda; el alto acompaña
            # la descripción y el sustento, en lugar de fijar todas a 42 pt.
            hoja.row_dimensions[fila_excel].height = min(409.5, max(42, lineas * 14 + 8))
            fila_excel += 1
        hoja.merge_cells(start_row=fila_excel, start_column=1, end_row=fila_excel, end_column=6)
        texto(hoja.cell(fila_excel, 1), 'TOTAL POR COMPLETAR (USD)' if importes_pendientes
              else 'TOTAL DE REQUERIMIENTOS (USD)')
        if importes_pendientes:
            hoja.cell(fila_excel, 7).comment = Comment(
                f'Completa los importes de {importes_pendientes} necesidad(es) de esta hoja. '
                'No se presenta una suma parcial como total del requerimiento.', 'Sistema de unidades')
        else:
            hoja.cell(fila_excel, 7, f'=SUM(G5:G{fila_excel - 1})' if fila_excel > 5 else '=0')
        hoja.cell(fila_excel, 7).number_format = '#,##0.00'
        for celda in hoja[fila_excel][:ultima]:
            celda.font = Font(name='Arial', size=10, bold=True, color=verde)
            celda.border = borde
        hoja.auto_filter.ref = f'A4:{get_column_letter(ultima)}{max(4, fila_excel - 1)}'
        hoja.freeze_panes = 'D5'
        for columna, ancho in enumerate(anchos, 1):
            hoja.column_dimensions[get_column_letter(columna)].width = ancho
        hoja.row_dimensions[2].height = 30
        hoja.row_dimensions[4].height = 35
        hoja.sheet_view.showGridLines = False
        hoja.sheet_properties.pageSetUpPr.fitToPage = True
        hoja.page_setup.orientation = 'landscape'
        hoja.page_setup.paperSize = hoja.PAPERSIZE_A3
        hoja.page_setup.fitToWidth = 1
        hoja.page_setup.fitToHeight = 0
        hoja.print_title_rows = '1:4'
        hoja.print_area = f'A1:{get_column_letter(ultima)}{fila_excel}'
    if contenido.get('pac_version') == PAC_VERSION:
        # Complemento local: las tres matrices anteriores conservan exactamente
        # las columnas universitarias. Una fila equivale a una compra y un mes.
        hoja = libro.create_sheet('PROGRAMACION')
        con_clase = contenido.get('clases_bien_version') == 1
        cabecera_programacion = ENCABEZADOS_PROGRAMACION_CLASES if con_clase else ENCABEZADOS_PROGRAMACION
        con_fases = contenido.get('inversion_gestion_version') == 1
        if con_fases:
            cabecera_programacion = (*cabecera_programacion, *ENCABEZADOS_FASES)
        ultima_programacion = len(cabecera_programacion)
        letra_final_programacion = get_column_letter(ultima_programacion)
        for numero, titulo in ((1, 'UNIVERSIDAD POLITÉCNICA ESTATAL DEL CARCHI'),
            (2, f'PROGRAMACIÓN DE NECESIDADES DE BIENES Y SERVICIOS {anio_planificado}'),
            (3, f'{unidad_nombre} · ' + ('BORRADOR' if borrador else 'REQUERIMIENTOS REGISTRADOS'))):
            hoja.merge_cells(start_row=numero, start_column=1, end_row=numero, end_column=ultima_programacion)
            texto(hoja.cell(numero, 1), titulo)
            hoja.cell(numero, 1).font = Font(name='Arial', size=11, bold=True, color=verde)
            hoja.cell(numero, 1).alignment = Alignment(horizontal='center', wrap_text=True)
        hoja['A3'].comment = Comment('Mes previsto, pendiente de la gestión y disponibilidad presupuestaria. '
            'Una misma necesidad en meses distintos debe distribuir sus cantidades entre filas; '
            'no se duplica el total. No constituye autorización de gasto.', 'Sistema de unidades')
        for columna, etiqueta in enumerate(cabecera_programacion, 1):
            celda = hoja.cell(4, columna, etiqueta)
            celda.font = Font(name='Arial', size=10, bold=True, color='FFFFFF')
            celda.fill = PatternFill('solid', fgColor=verde)
            celda.alignment = Alignment(wrap_text=True, vertical='center')
            celda.border = borde
        anchos = [27, 25, 42, 56, 13, 17, 19, 13, 17, 65]
        if con_clase:
            anchos.append(25)
        if con_fases:
            anchos.extend([36, 10, 60, 60])
        importes_pendientes = 0
        for numero, fila in enumerate(filas, 5):
            mes = _mes(fila.get('mes_compra'))
            valores = [fila.get('area_nombre', ''), dict(TIPOS_NECESIDAD).get(fila.get('tipo_necesidad'), ''),
                fila.get('equipo_referencia', ''), fila.get('item', ''), _numero(fila.get('cantidad')),
                _numero(fila.get('costo_unitario')), None, semestre_compra(mes),
                dict(MESES_COMPRA).get(str(mes), ''), unescape(strip_tags(_texto(fila.get('justificacion'))))]
            if con_clase:
                valores.append(dict(clases_bien_de(contenido)).get(fila.get('clase_bien'), 'Por confirmar'))
            if con_fases:
                valores.extend([fila.get('grupo_fases', ''), str(_fase(fila.get('fase_numero')) or ''),
                    strip_tags(_texto(fila.get('resultado_fase'))),
                    strip_tags(_texto(fila.get('condicion_siguiente_fase')))])
            for columna, valor in enumerate(valores, 1):
                celda = hoja.cell(numero, columna)
                if columna in (5, 6, 8):
                    celda.value = valor
                    celda.number_format = '#,##0.00' if columna == 6 else '0.###' if columna == 5 else '0'
                elif columna != 7:
                    texto(celda, valor)
                celda.font = Font(name='Arial', size=10)
                celda.alignment = Alignment(vertical='top', wrap_text=True)
                celda.border = borde
            if valores[4] is not None and valores[4] > 0 and valores[5] is not None:
                hoja.cell(numero, 7, f'=E{numero}*F{numero}').number_format = '#,##0.00'
            else:
                importes_pendientes += 1
                hoja.cell(numero, 7).comment = Comment('Completa la cantidad positiva y el valor unitario no negativo.', 'Sistema de unidades')
            if mes is None:
                for columna in (8, 9):
                    hoja.cell(numero, columna).fill = PatternFill('solid', fgColor='FFF2CC')
                    hoja.cell(numero, columna).comment = Comment('Selecciona el mes previsto; el trimestre anterior no determina un mes exacto.', 'Sistema de unidades')
            lineas = max(sum(max(1, ceil(len(parte) / max(8, ancho - 2))) for parte in _texto(valor).split('\n'))
                         for valor, ancho in zip(valores, anchos))
            hoja.row_dimensions[numero].height = min(409.5, max(42, lineas * 14 + 8))
        final = len(filas) + 5
        hoja.merge_cells(start_row=final, start_column=1, end_row=final, end_column=6)
        texto(hoja.cell(final, 1), 'TOTAL POR COMPLETAR (USD)' if importes_pendientes else 'TOTAL DE REQUERIMIENTOS (USD)')
        if importes_pendientes:
            hoja.cell(final, 7).comment = Comment('Completa los importes pendientes. No se presenta una suma parcial como total.', 'Sistema de unidades')
        else:
            hoja.cell(final, 7, f'=SUM(G5:G{final - 1})' if filas else '=0').number_format = '#,##0.00'
        for celda in hoja[final][:ultima_programacion]:
            celda.font = Font(name='Arial', size=10, bold=True, color=verde)
            celda.border = borde
        for columna, ancho in enumerate(anchos, 1):
            hoja.column_dimensions[get_column_letter(columna)].width = ancho
        hoja.row_dimensions[2].height = 30
        hoja.row_dimensions[3].height = 30
        hoja.row_dimensions[4].height = 35
        hoja.auto_filter.ref = f'A4:{letra_final_programacion}{max(4, final - 1)}'
        hoja.freeze_panes = 'D5'
        hoja.sheet_view.showGridLines = False
        hoja.sheet_properties.pageSetUpPr.fitToPage = True
        hoja.page_setup.orientation = 'landscape'
        hoja.page_setup.paperSize = hoja.PAPERSIZE_A3
        hoja.page_setup.fitToWidth, hoja.page_setup.fitToHeight = 1, 0
        hoja.print_title_rows = '1:4'
        hoja.print_area = f'A1:{letra_final_programacion}{final}'
    if contenido.get('matriz_detalle_version') == 1:
        # Vista de trabajo por clase. No altera las columnas del PAC universitario.
        hoja = libro.create_sheet('DETALLE POR CLASE')
        cabecera = ('CLASE', 'NOMBRE DEL BIEN O SERVICIO', 'ESPECIFICACIONES', 'UNIDAD DE MEDIDA',
            'CANTIDAD', 'V. UNITARIO', 'TOTAL', 'CPC', 'GRUPO', 'PARTIDA', 'PAC/NO PAC',
            'FUENTE DE FINANCIAMIENTO', 'ÁREA', 'MES', 'SEMESTRE', 'JUSTIFICACIÓN', 'OBSERVACIONES')
        for numero, titulo in ((1, 'UNIVERSIDAD POLITÉCNICA ESTATAL DEL CARCHI'),
                (2, f'DETALLE DE NECESIDADES POR CLASE · {anio_planificado}'),
                (3, f'{unidad_nombre} · ' + ('BORRADOR' if borrador else 'REQUERIMIENTOS REGISTRADOS'))):
            hoja.merge_cells(start_row=numero, start_column=1, end_row=numero, end_column=len(cabecera))
            texto(hoja.cell(numero, 1), titulo)
            hoja.cell(numero, 1).font = Font(name='Arial', size=11, bold=True, color=verde)
            hoja.cell(numero, 1).alignment = Alignment(horizontal='center', wrap_text=True)
        for columna, etiqueta in enumerate(cabecera, 1):
            celda = hoja.cell(4, columna, etiqueta)
            celda.font = Font(name='Arial', size=10, bold=True, color='FFFFFF')
            celda.fill = PatternFill('solid', fgColor=verde)
            celda.alignment = Alignment(wrap_text=True, vertical='center')
            celda.border = borde
        catalogo = dict(CLASES_BIEN)
        orden = {clave: posicion for posicion, (clave, _) in enumerate(CLASES_BIEN)}
        filas_ordenadas = sorted(enumerate(filas), key=lambda par: (orden.get(par[1].get('clase_bien'), 99), par[0]))
        pendientes = 0
        for numero, (_, fila) in enumerate(filas_ordenadas, 5):
            mes = _mes(fila.get('mes_compra'))
            valores = [catalogo.get(fila.get('clase_bien'), 'Por confirmar'), fila.get('item', ''),
                fila.get('especificaciones', ''), fila.get('unidad_medida', ''), _numero(fila.get('cantidad')),
                _numero(fila.get('costo_unitario')), None, fila.get('cpc', ''), _texto(fila.get('partida'))[:2],
                fila.get('partida', ''), {'pac': 'PAC', 'no_pac': 'NOPAC'}.get(_clasificacion(fila.get('clasificacion_pac')), ''),
                fila.get('fuente_pac', ''), fila.get('area_nombre', ''), dict(MESES_COMPRA).get(str(mes), ''),
                semestre_compra(mes), strip_tags(_texto(fila.get('justificacion'))), fila.get('observaciones', '')]
            for columna, valor in enumerate(valores, 1):
                celda = hoja.cell(numero, columna)
                if columna in (5, 6, 15):
                    celda.value = valor
                elif columna != 7:
                    texto(celda, valor)
                celda.font = Font(name='Arial', size=10)
                celda.alignment = Alignment(vertical='top', wrap_text=True)
                celda.border = borde
                if columna in (6, 7):
                    celda.number_format = '#,##0.00'
                elif columna == 5:
                    celda.number_format = '0.###'
                elif columna in (8, 9, 10, 12):
                    celda.number_format = '@'
            if valores[4] is not None and valores[4] > 0 and valores[5] is not None:
                hoja.cell(numero, 7, f'=E{numero}*F{numero}').number_format = '#,##0.00'
            else:
                pendientes += 1
            hoja.row_dimensions[numero].height = min(409.5, max(42, ceil(max(len(_texto(v)) for v in valores) / 45) * 14 + 8))
        final = len(filas) + 5
        hoja.merge_cells(start_row=final, start_column=1, end_row=final, end_column=6)
        texto(hoja.cell(final, 1), 'TOTAL POR COMPLETAR (USD)' if pendientes else 'TOTAL DE REQUERIMIENTOS (USD)')
        if not pendientes:
            hoja.cell(final, 7, f'=SUM(G5:G{final - 1})' if filas else '=0').number_format = '#,##0.00'
        for columna, ancho in enumerate((25, 45, 70, 23, 13, 17, 19, 19, 10, 17, 16, 25, 30, 17, 13, 70, 50), 1):
            hoja.column_dimensions[get_column_letter(columna)].width = ancho
        hoja.row_dimensions[4].height = 35
        hoja.auto_filter.ref = f'A4:Q{max(4, final - 1)}'
        hoja.freeze_panes = 'C5'
        hoja.sheet_view.showGridLines = False
        hoja.sheet_properties.pageSetUpPr.fitToPage = True
        hoja.page_setup.orientation = 'landscape'
        hoja.page_setup.paperSize = hoja.PAPERSIZE_A3
        hoja.page_setup.fitToWidth, hoja.page_setup.fitToHeight = 1, 0
        hoja.print_title_rows = '1:4'
        hoja.print_area = f'A1:Q{final}'
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()
