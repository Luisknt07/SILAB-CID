"""Contraste de necesidades con una única captura de inventario y operación.

No consulta ni modifica registros. Una coincidencia identifica antecedentes;
no certifica equivalencia técnica, capacidad libre ni autorización de compra.
"""
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import json
import re
import unicodedata


VERSION = 1
_CERRADAS = {'resuelta', 'cerrada', 'cancelada', 'descartada'}
_MANTENIMIENTO_TERMINADO = {'completado', 'cancelado'}


def _texto(valor):
    return str(valor if valor is not None else '').strip()


def _normalizado(valor):
    texto = unicodedata.normalize('NFKD', _texto(valor).casefold())
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in texto if not unicodedata.combining(c))).split())


def _lista(valor):
    return valor if isinstance(valor, list) else []


def _ids(valor):
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except (TypeError, ValueError):
            return []
    return list(dict.fromkeys(str(int(v)) for v in _lista(valor)
        if not isinstance(v, bool) and str(v).isdecimal() and int(v) > 0))


def _numero(valor):
    try:
        numero = Decimal(str(valor).replace(',', '.'))
        return numero if numero.is_finite() and numero >= 0 else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def _serializable(valor):
    return json.loads(json.dumps(valor, default=str, ensure_ascii=False))


def _equipos(lectura, areas):
    resultado = {}
    for original in _lista((lectura.get('fuentes') or {}).get('equipos')):
        if not isinstance(original, dict) or not original.get('id'):
            continue
        identificador = str(original['id'])
        if identificador in resultado:
            continue
        uso = original.get('desgaste') or {}
        incidentes = deepcopy(_lista(original.get('incidencias')))
        mantenimientos = deepcopy(_lista(original.get('mantenimientos')))
        resultado[identificador] = dict(id=original['id'], nombre=original.get('nombre', ''),
            codigo=original.get('codigo', ''), modelo_id=original.get('modelo_id'),
            familia_id=original.get('familia_id'), familia=original.get('familia_nombre', ''),
            estado=original.get('estado_label') or original.get('estado', ''),
            estado_codigo=original.get('estado', ''), vigente=bool(original.get('activo', True) and not original.get('baja')),
            area_principal_id=str(original.get('area_principal_id') or '0'),
            areas=[dict(id=str(a), nombre=areas.get(str(a), {}).get('nombre', 'Área no identificada'),
                        activa=areas.get(str(a), {}).get('activa', False)) for a in original.get('areas_ids') or []],
            horas=uso.get('horas_documentadas', 0), periodos=deepcopy(_lista(original.get('uso_semestres'))),
            vida_util=dict(fin=original.get('vida_util_referencia_fin'), limite_horas=uso.get('limite_horas')),
            garantia=deepcopy(original.get('garantia') or {}),
            incidencias=incidentes, mantenimiento=mantenimientos,
            incidencias_abiertas=sum(i.get('estado') not in _CERRADAS for i in incidentes),
            mantenimiento_pendiente=sum(m.get('estado') not in _MANTENIMIENTO_TERMINADO for m in mantenimientos),
            uso_pendiente=deepcopy(_lista(original.get('uso_pendiente'))), url=original.get('url', ''))
    return resultado


def _disponible(equipo):
    # Un estado legado puede no haber seguido la incidencia o la orden.
    # El bloqueo capturado impide ofrecer ese activo como alternativa libre;
    # no sustituye ni modifica su condición registrada en el inventario.
    bloqueo = any(i.get('detiene_operacion') and i.get('estado') not in _CERRADAS
                  for i in equipo['incidencias'])
    en_mantenimiento = any(m.get('estado') == 'en_proceso' for m in equipo['mantenimiento'])
    return equipo['vigente'] and equipo['estado_codigo'] == 'disponible' and not bloqueo and not en_mantenimiento


def _mismo_recurso(equipo, nombre, modelos=(), familias=()):
    return bool((equipo.get('modelo_id') and equipo['modelo_id'] in modelos)
        or (equipo.get('familia_id') and equipo['familia_id'] in familias)
        or (_normalizado(nombre) and _normalizado(nombre) == _normalizado(equipo['nombre'])))


def _uso(equipos):
    # Las horas se presentan por activo; no equivalen a ocupación del área.
    periodos = defaultdict(lambda: dict(horas=0, reservas=set(), sesiones_sin_id=0))
    pendientes = []
    for equipo in equipos:
        for periodo in equipo['periodos']:
            fila = periodos[periodo.get('periodo', '')]
            fila['horas'] += periodo.get('horas', 0)
            # Una misma reserva puede utilizar varios activos. Su identidad
            # permite contar la sesión una vez, conservando las horas por activo.
            reservas = {int(pk) for pk in _ids(periodo.get('reservas'))}
            fila['reservas'].update(reservas)
            fila['sesiones_sin_id'] += max(0, periodo.get('sesiones', 0) - len(reservas))
        pendientes.extend(equipo['uso_pendiente'])
    if any(p['sesiones_sin_id'] for p in periodos.values()):
        pendientes.append(dict(motivos=['Hay sesiones en la captura sin identidad de reserva; no se puede verificar su total único.']))
    return dict(horas=round(sum(e['horas'] for e in equipos), 2),
        periodos=[dict(periodo=k, horas=round(v['horas'], 2), reservas=sorted(v['reservas']),
                       sesiones=None if v['sesiones_sin_id'] else len(v['reservas'])) for k, v in periodos.items()],
        pendientes=pendientes, alcance='Horas acumuladas por activo; no sumar como ocupación de espacios.')


def _referencia_formulario(fila):
    return {**{k: _texto(fila.get(k)) for k in ('item', 'clase_bien', 'area_id', 'tipo_necesidad', 'cantidad', 'unidad_medida')},
            'equipos_referencia': _ids(fila.get('equipos_referencia'))}


def _referencias_area(area, equipos, recursos):
    referencias, sugerencias = [], []
    originales, procesos_por_modelo = [], {}
    for original in _lista(area.get('dotacion_referencia')):
        referencia = deepcopy(original)
        if referencia.get('origen') == 'etapa_proceso' and referencia.get('modelo_id'):
            proceso = {k: referencia.get(k) for k in (
                'receta_id', 'receta_codigo', 'receta_nombre', 'estado_receta', 'id', 'para_que')}
            previa = procesos_por_modelo.get(referencia['modelo_id'])
            if previa is not None:
                previa['procesos'].append(proceso)
                continue  # Varias etapas no representan varios equipos requeridos.
            referencia['procesos'] = [proceso]
            procesos_por_modelo[referencia['modelo_id']] = referencia
        originales.append(referencia)
    for referencia in originales:
        tipo = referencia.get('tipo')
        campo_vinculo = {'equipo': 'registrado_id', 'software': 'software_registrado_id',
                         'insumo': 'insumo_registrado_id'}.get(tipo, 'registrado_id')
        vinculo = str(referencia.get(campo_vinculo) or '')
        vinculado = (equipos if tipo == 'equipo' else recursos.get(tipo, {})).get(vinculo)
        modelos = {referencia['modelo_id']} if referencia.get('modelo_id') else set()
        familias = {referencia['familia_id']} if referencia.get('familia_id') else set()
        if vinculado and vinculado.get('modelo_id'):
            modelos.add(vinculado['modelo_id'])
        candidatos = [e for e in equipos.values() if e['vigente'] and _mismo_recurso(e,
                      referencia.get('nombre'), modelos, familias)] if referencia.get('tipo') == 'equipo' else []
        locales = [e for e in candidatos if str(area['id']) in {a['id'] for a in e['areas']}]
        referencia.update(estado='vinculada' if vinculado else 'por_verificar',
            activos_relacionados=[e['id'] for e in locales], alternativas=[e['id'] for e in candidatos if _disponible(e)],
            recurso_registrado=deepcopy(vinculado) if tipo != 'equipo' else None,
            carencia_confirmada=False,
            lectura=('Dotación propuesta por evaluar; no acredita adquisición, existencia ni instalación.' if referencia.get('solo_referencia') else
                     'Referencia funcional con vínculo al inventario; confirme prestaciones y capacidad.' if vinculado else
                     'Referencia de dotación por verificar; la falta de vínculo no demuestra ausencia física.'))
        referencias.append(referencia)
        if not area.get('activa', True) or locales or referencia.get('tipo') != 'equipo' or not referencia.get('nombre'):
            continue
        motivo = ('La ficha o el proceso del área identifica esta función. No hay un activo coincidente vinculado al área '
                  'en la captura; verifique inventario, asignaciones y posibilidad de compartir antes de definir una compra.')
        if referencia.get('solo_referencia'):
            motivo = ('Capacidad propuesta para estudio, no un requisito mínimo ni una carencia confirmada. '
                      'Contraste la demanda, el inventario y alternativas compartidas o externas antes de dimensionar una compra.')
        if referencia.get('para_que'):
            motivo += ' Función registrada: ' + str(referencia['para_que']).strip()
        if referencia.get('fuente'):
            motivo += ' Fuente: ' + str(referencia['fuente']).strip()
        if (referencia.get('estado_receta') in ('referencia', 'derivado') or any(
                p.get('estado_receta') in ('referencia', 'derivado') for p in referencia.get('procesos') or [])):
            motivo += ' El proceso es una referencia o propuesta derivada y requiere validación operativa.'
        sugerencias.append(dict(clave=f"referencia-area:{area['id']}:{referencia.get('origen')}:{referencia.get('id')}",
            area_id=str(area['id']), area_nombre=area['nombre'], item=referencia['nombre'], clase_bien='equipos',
            tipo_necesidad='dotacion', equipos_referencia=[], cantidad='',
            estado='por_verificar', carencia_confirmada=False, origen=referencia.get('origen', 'ficha_area'),
            accion='Verificar dotación y alternativas', motivo=motivo, fuente=deepcopy(referencia)))
    return referencias, sugerencias


def _areas(lectura, equipos):
    salida = []
    recursos = {'software': {}, 'insumo': {}}
    for grupo in _lista(lectura.get('recursos_clases')):
        tipo = 'software' if grupo.get('clave') == 'software' else 'insumo' if grupo.get('clave') in (
            'materiales', 'insumos', 'reactivos') else None
        if tipo:
            recursos[tipo].update({str(r['id']): r for r in grupo.get('filas') or [] if r.get('id')})
    for original in _lista(lectura.get('areas')):
        if not isinstance(original, dict):
            continue
        area = deepcopy(original)
        identificador = str(area['id'])
        actuales = [e for e in equipos.values() if e['vigente'] and e['area_principal_id'] == identificador]
        asociados = [e for e in equipos.values() if e['vigente'] and identificador in {a['id'] for a in e['areas']}]
        disponibles = [e for e in actuales if _disponible(e)]
        referencias, sugerencias = _referencias_area(area, equipos, recursos)
        avisos = []
        if not area.get('activa', True):
            avisos.append('Área inactiva: confirmar su habilitación antes de programar dotación.')
        if not actuales:
            avisos.append('Sin activos vigentes asignados como área principal; revise recursos compartidos y vínculos del inventario.')
        if not area.get('funcion') and not area.get('aplicaciones') and not referencias:
            avisos.append('Complete las funciones y la dotación de referencia del área; no hay base para deducir equipos mínimos.')
        if not disponibles and area.get('politica_reserva') == 'tecnico':
            avisos.append('La política exige recurso técnico; compruebe equipos y software disponibles antes de habilitar la actividad.')
        if any(not u.get('sesiones') for u in area.get('uso_semestres') or []):
            avisos.append('Un semestre sin uso acreditado requiere revisar programación y cierres; no justifica comprar equipos.')
        claves = set(area.get('sugerencias') or [])
        if area.get('activa', True):
            sugerencias.extend(deepcopy(s) for s in _lista(lectura.get('sugerencias')) if s.get('clave') in claves)
        salida.append(dict(id=identificador, nombre=area['nombre'], activa=area.get('activa', True),
            funcion=area.get('funcion', ''), aplicaciones=area.get('aplicaciones', ''),
            fuente_funcion=area.get('fuente_funcion', ''), politica_reserva=area.get('politica_reserva', ''),
            capacidad_usuarios=area.get('capacidad_usuarios'), equipos_actuales=len(actuales),
            equipos_disponibles=len(disponibles), equipos_asociados=len(asociados),
            equipos_compartidos=sum(e['area_principal_id'] != identificador for e in asociados),
            uso_semestres=deepcopy(area.get('uso_semestres') or []),
            referencias=referencias, sugerencias=sugerencias, avisos=avisos))
        salida[-1]['referencias_vinculadas'] = sum(r['estado'] == 'vinculada' for r in referencias)
        salida[-1]['referencias_por_verificar'] = sum(r['estado'] != 'vinculada' for r in referencias)
    return salida


def _existencias(fila, diagnostico):
    clase = fila.get('clase_bien')
    if clase == 'equipos' or clase == 'servicios':
        return []
    candidatas = []
    for grupo in _lista(diagnostico.get('recursos_clases')):
        if grupo.get('clave') != clase:
            continue
        for recurso in grupo.get('filas') or []:
            if _normalizado(recurso.get('nombre')) == _normalizado(fila.get('item')):
                candidatas.append(deepcopy(recurso))
    return candidatas


def _contraste_fila(fila, numero, lectura, equipos, areas):
    identificador = _texto(fila.get('id_necesidad'))
    area_id = _texto(fila.get('area_id'))
    area = areas.get(area_id)
    pendientes = []
    ids = _ids(fila.get('equipos_referencia'))
    existentes = [equipos[pk] for pk in ids if pk in equipos]
    if any(pk not in equipos for pk in ids):
        pendientes.append('Hay un equipo seleccionado que no pertenece a esta captura de la unidad.')
    if area_id not in ('unidad', '') and (not area or not area['activa']):
        pendientes.append('El área de destino no está identificada como activa; revise la selección.')
    modelos = {e['modelo_id'] for e in existentes if e.get('modelo_id')}
    familias = {e['familia_id'] for e in existentes if e.get('familia_id')}
    coincidencias = [e for e in equipos.values() if e['vigente'] and _mismo_recurso(e, fila.get('item'), modelos, familias)]
    if not existentes and fila.get('clase_bien') == 'equipos':
        existentes = coincidencias
    elegidos = {e['id'] for e in existentes}
    alternativas = [e for e in coincidencias if _disponible(e) and e['id'] not in elegidos]
    catalogadas = _existencias(fila, lectura)
    recursos = [r for r in catalogadas if not r.get('es_referencia')]
    referencias_tecnicas = [r for r in catalogadas if r.get('es_referencia')]
    if referencias_tecnicas:
        pendientes.append('El catálogo describe piezas de referencia por modelo; no acredita existencias de repuestos en bodega.')
    abiertos = sum(e['incidencias_abiertas'] for e in existentes)
    mantenimiento = sum(e['mantenimiento_pendiente'] for e in existentes)
    reparaciones = [deepcopy(r) for r in _lista((lectura.get('fuentes') or {}).get('reparaciones'))
                   if str(r.get('equipo_id')) in {str(e['id']) for e in existentes}]
    estado, etiqueta = 'por_contrastar', 'Contraste por completar'
    resumen = 'Identifique qué recursos actuales sustentan la necesidad y qué capacidad o función se requiere.'
    if existentes:
        estado, etiqueta = 'antecedentes_identificados', 'Recursos actuales identificados'
        resumen = f'{len(existentes)} activo(s) relacionado(s); contraste sus prestaciones, uso y condición con lo solicitado.'
    if recursos:
        estado, etiqueta = 'existencias_registradas', 'Existencias o licencias registradas'
        resumen = 'Existe un recurso con el mismo nombre; revise cantidad, presentación, licencias y consumo antes de ampliar.'
    danados = [e for e in existentes if e['vigente'] and e['estado_codigo'] == 'dañado']
    sin_disponibilidad = [e for e in existentes if e['vigente'] and e['estado_codigo'] in (
        'no_disponible', 'en_uso', 'prestado', 'mantenimiento')]
    no_localizados = [e for e in existentes if e['vigente'] and e['estado_codigo'] == 'no_localizado']
    obsoletos = [e for e in existentes if e['vigente'] and e['estado_codigo'] == 'obsoleto']
    if sin_disponibilidad:
        pendientes.append('Hay activos en uso, prestados, en mantenimiento o no disponibles; verifique el motivo y su retorno antes de deducir falta de dotación.')
    if no_localizados:
        pendientes.append('Hay activos no localizados; verifique existencia, custodia y trazabilidad antes de justificar su sustitución.')
    if obsoletos:
        pendientes.append('El inventario declara obsolescencia; sustente las prestaciones que faltan y las alternativas técnicas antes de reemplazar.')
    if danados or abiertos or mantenimiento:
        estado, etiqueta = 'revision_tecnica', 'Revisión técnica y reparación'
        resumen = 'Revise las incidencias, garantías, repuestos y mantenimiento antes de decidir la sustitución completa.'
        if not any((r.get('recomendacion') or {}).get('decision') == 'reemplazar' for r in reparaciones):
            pendientes.append('No se identifica una recomendación técnica de reemplazo; una avería no acredita daño irreparable.')
    if alternativas:
        pendientes.append('Hay equipos disponibles del mismo modelo, familia o nombre en la unidad; comprobar compatibilidad, agenda y uso compartido.')
    if existentes and not any(e['horas'] for e in existentes):
        pendientes.append('No hay horas acreditadas en estos activos; verificar cierres y planificación, sin asumir desuso ni necesidad de compra.')
    if any(e['uso_pendiente'] for e in existentes):
        pendientes.append('Existen cierres pendientes de identificar; el registro incompleto no acredita falta de uso.')
    if fila.get('tipo_necesidad') == 'ampliacion':
        pendientes.append('La ampliación requiere comparar demanda simultánea y capacidad disponible; el conteo de equipos no mide saturación.')
    if not existentes and not recursos:
        pendientes.append('Sin vínculo o coincidencia identificable con el inventario; esto no demuestra que el bien no exista.')
    return dict(id_necesidad=identificador, numero=numero, item=_texto(fila.get('item')), area_id=area_id,
        area_nombre=(area or {}).get('nombre') or ('Toda la unidad' if area_id == 'unidad' else 'Área por revisar'),
        estado=estado, etiqueta=etiqueta, resumen=resumen, existentes=deepcopy(existentes),
        alternativas=deepcopy(alternativas), existencias=recursos, referencias_tecnicas=referencias_tecnicas,
        uso=_uso(existentes),
        tecnico=dict(incidencias_abiertas=abiertos, mantenimiento_pendiente=mantenimiento, reparaciones=reparaciones),
        pendientes=list(dict.fromkeys(pendientes)), referencia_formulario=_referencia_formulario(fila))


def contrastar_compras(contenido, diagnostico):
    """Lectura JSON para el editor, usando las mismas fuentes de su diagnóstico."""
    salida = dict(version=VERSION, disponible=False, fecha_corte='', areas=[], necesidades=[],
                  por_necesidad={}, por_equipo={})
    if not isinstance(diagnostico, dict) or not isinstance(diagnostico.get('areas'), list):
        return salida
    areas = {str(a['id']): a for a in diagnostico['areas'] if isinstance(a, dict) and 'id' in a}
    equipos = _equipos(diagnostico, areas)
    salida.update(disponible=True, fecha_corte=diagnostico.get('fecha_corte', ''), por_equipo=equipos,
                  areas=_areas(diagnostico, equipos))
    for numero, fila in enumerate(_lista((contenido or {}).get('compras')), 1):
        if not isinstance(fila, dict) or not _texto(fila.get('item')):
            continue
        contraste = _contraste_fila(fila, numero, diagnostico, equipos, areas)
        salida['necesidades'].append(contraste)
        if contraste['id_necesidad']:
            salida['por_necesidad'][contraste['id_necesidad']] = contraste
    return _serializable(salida)
