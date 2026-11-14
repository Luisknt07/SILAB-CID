"""Estado de equipos existentes y respaldo de las compras, agrupados por áreas."""
from collections import Counter, OrderedDict
from datetime import date
from math import isfinite


_ESTADOS = {'disponible': 'Disponible', 'en_uso': 'En uso', 'mantenimiento': 'En mantenimiento',
    'dañado': 'Dañado', 'prestado': 'Prestado', 'no_disponible': 'No disponible',
    'obsoleto': 'Obsoleto', 'no_localizado': 'No localizado'}
_INCIDENCIAS_CERRADAS = {'resuelta', 'cerrada', 'descartada', 'cancelada'}
_MANTENIMIENTOS_TERMINADOS = {'completado', 'cancelado'}


def _etiqueta_estado(equipo):
    estado = equipo.get('estado') or ''
    return equipo.get('estado_label') or _ESTADOS.get(estado, estado if estado else 'Sin estado registrado')


def _fecha_referencia(valor):
    try:
        return date.fromisoformat(str(valor))
    except (ValueError, TypeError):
        return None


def _horas_referencia(valor):
    try:
        numero = float(valor)
        return numero if isfinite(numero) and numero >= 0 else 0
    except (TypeError, ValueError):
        return 0


def _pendientes_tecnicos(registros, cerrados):
    vistos, pendientes = set(), 0
    for indice, registro in enumerate(registros or []):
        if not isinstance(registro, dict):
            continue
        identidad = str(registro['id']) if registro.get('id') is not None else ('sin_id', indice)
        if identidad in vistos:
            continue
        vistos.add(identidad)
        pendientes += registro.get('estado') not in cerrados
    return pendientes


def _vida_util_equipos(equipos, fecha):
    resultado = dict(sin_fecha=0, fecha_cumplida=0, fecha_vigente=0, sin_limite_horas=0,
                     referencia_horas_alcanzada=0)
    for equipo in equipos:
        fin = _fecha_referencia(equipo.get('vida_util_referencia_fin'))
        resultado['sin_fecha' if not fin or not fecha else 'fecha_cumplida' if fin <= fecha else 'fecha_vigente'] += 1
        desgaste = equipo.get('desgaste') or {}
        limite = _horas_referencia(desgaste.get('limite_horas'))
        if not limite:
            resultado['sin_limite_horas'] += 1
        elif _horas_referencia(desgaste.get('horas_documentadas')) >= limite:
            resultado['referencia_horas_alcanzada'] += 1
    return resultado


def _uso_equipos(equipos):
    periodos, pendientes = OrderedDict(), set()
    for equipo in equipos:
        for indice, pendiente in enumerate(equipo.get('uso_pendiente') or []):
            reserva = (pendiente.get('reserva_id') or pendiente.get('reserva')) if isinstance(pendiente, dict) else pendiente
            identidad = (('reserva', str(int(reserva))) if not isinstance(reserva, bool)
                         and str(reserva).isdecimal() and int(reserva) > 0 else ('sin_id', equipo['id'], indice))
            pendientes.add(identidad)
        for fuente in equipo.get('uso_semestres') or []:
            if not isinstance(fuente, dict):
                continue
            periodo = periodos.setdefault(str(fuente.get('periodo') or 'Sin semestre identificado'),
                dict(horas=0, reservas=set(), sin_identidad=False))
            periodo['horas'] += _horas_referencia(fuente.get('horas'))
            ids = {str(int(v)) for v in fuente.get('reservas') or [] if not isinstance(v, bool) and str(v).isdecimal() and int(v) > 0}
            periodo['reservas'].update(ids)
            if (_horas_referencia(fuente.get('sesiones')) > len(ids)
                    or (not ids and (fuente.get('sesiones') is None or _horas_referencia(fuente.get('horas')) > 0))):
                periodo['sin_identidad'] = True
    return dict(horas=round(sum(_horas_referencia((e.get('desgaste') or {}).get('horas_documentadas')) for e in equipos), 2),
        pendientes=len(pendientes), periodos=[dict(periodo=nombre, horas=round(p['horas'], 2),
            sesiones=None if p['sin_identidad'] else len(p['reservas'])) for nombre, p in periodos.items()])


def _modelos_estado(equipos, fecha):
    grupos = OrderedDict()
    for equipo in equipos:
        modelo = ('id', str(equipo['modelo_id'])) if equipo.get('modelo_id') else ('nombre', equipo.get('nombre') or '')
        clave = (modelo, equipo.get('estado') or '')
        grupos.setdefault(clave, []).append(equipo)
    resultado = []
    for (_, estado), activos in grupos.items():
        primero = activos[0]
        uso = _uso_equipos(activos)
        resultado.append(dict(modelo_id=primero.get('modelo_id'), nombre=primero.get('nombre') or 'Modelo no identificado',
            estado_codigo=estado, estado=_etiqueta_estado(primero),
            cantidad=len(activos), codigos=list(dict.fromkeys(e.get('codigo') for e in activos if e.get('codigo'))),
            compartidos=sum(len(set(str(i) for i in e.get('areas_ids') or [])) > 1 for e in activos),
            incidencias_abiertas=sum(_pendientes_tecnicos(e.get('incidencias'), _INCIDENCIAS_CERRADAS) for e in activos),
            mantenimiento_pendiente=sum(_pendientes_tecnicos(e.get('mantenimientos'), _MANTENIMIENTOS_TERMINADOS) for e in activos),
            vida_util=_vida_util_equipos(activos, fecha), uso_semestres=uso['periodos'],
            horas=uso['horas'], uso_pendiente=uso['pendientes']))
    return resultado


def resumen_estado_equipos(lectura):
    """Estado completo por área de la captura; no consulta ni actualiza inventario."""
    lectura = lectura if isinstance(lectura, dict) else {}
    fuentes = lectura.get('fuentes') or {}
    disponibles = isinstance(fuentes.get('equipos'), list)
    fecha = _fecha_referencia(lectura.get('fecha_corte'))
    areas, equipos, vistos, avisos = OrderedDict(), [], set(), []
    for area in lectura.get('areas') or []:
        if not isinstance(area, dict) or area.get('id') is None:
            continue
        clave = str(area['id'])
        areas.setdefault(clave, dict(id=clave, nombre=area.get('nombre') or 'Área no identificada',
            activa=area.get('activa', True), _equipos=[]))
    for equipo in fuentes.get('equipos') or []:
        if not isinstance(equipo, dict) or equipo.get('id') is None:
            avisos.append('Hay registros sin identidad de activo; no se incluyen en los totales.')
            continue
        identificador = str(equipo['id'])
        if identificador in vistos:
            continue
        vistos.add(identificador)
        equipos.append(equipo)
        # Se respeta la asignación canónica capturada; no se elige otra área al leer.
        clave = str(equipo.get('area_principal_id') or '0')
        area = areas.setdefault(clave, dict(id=clave,
            nombre=equipo.get('area_principal_nombre') or ('Sin área asignada' if clave == '0' else 'Área por identificar'),
            activa=None, _equipos=[]))
        area['_equipos'].append(equipo)

    def completar(datos, activos):
        actuales = [e for e in activos if e.get('activo', True) and not e.get('baja')]
        bajas = [e for e in activos if e.get('baja')]
        inactivos = [e for e in activos if not e.get('activo', True) and not e.get('baja')]
        uso = _uso_equipos(actuales)
        estados = Counter(e.get('estado') or '' for e in actuales)
        etiquetas = {e.get('estado') or '': _etiqueta_estado(e) for e in actuales}
        datos.update(registrados=len(activos), vigentes=len(actuales), bajas=len(bajas), inactivos=len(inactivos),
            estados=[dict(codigo=k, nombre=etiquetas[k], cantidad=v) for k, v in estados.items()],
            compartidos=sum(len(set(str(i) for i in e.get('areas_ids') or [])) > 1 for e in actuales),
            incidencias_abiertas=sum(_pendientes_tecnicos(e.get('incidencias'), _INCIDENCIAS_CERRADAS) for e in actuales),
            mantenimiento_pendiente=sum(_pendientes_tecnicos(e.get('mantenimientos'), _MANTENIMIENTOS_TERMINADOS) for e in actuales),
            vida_util=_vida_util_equipos(actuales, fecha), uso_semestres=uso['periodos'], horas=uso['horas'], uso_pendiente=uso['pendientes'])
        return actuales, bajas, inactivos

    for area in areas.values():
        actuales, bajas, inactivos = completar(area, area.pop('_equipos'))
        area.update(modelos=_modelos_estado(actuales, fecha), modelos_baja=_modelos_estado(bajas, fecha),
                    modelos_inactivos=_modelos_estado(inactivos, fecha))
    totales = {}
    completar(totales, equipos)
    return dict(fecha=lectura.get('fecha_corte') or '', disponible=disponibles, areas=list(areas.values()),
        totales=totales, cierres_pendientes=len(fuentes.get('uso_recursos_pendiente') or []),
        avisos=list(dict.fromkeys(avisos)))


def _texto_vida_util(vida):
    total = sum(vida.get(k, 0) for k in ('sin_fecha', 'fecha_cumplida', 'fecha_vigente'))
    if total and vida['sin_fecha'] == total and vida['sin_limite_horas'] == total:
        return 'Vida útil sin fecha ni límite de horas registrados.'
    partes = []
    for clave, etiqueta in (('sin_fecha', 'sin fecha'), ('fecha_cumplida', 'con fecha referencial cumplida'),
                           ('fecha_vigente', 'con fecha referencial vigente'),
                           ('sin_limite_horas', 'sin límite por horas'),
                           ('referencia_horas_alcanzada', 'alcanzan la referencia de horas')):
        if vida.get(clave):
            partes.append(f"{vida[clave]} {etiqueta}")
    return '; '.join(partes) or 'Sin referencias de vida útil alcanzadas'


def _fila_estado_modelo(modelo):
    cantidad = str(modelo['cantidad'])
    if modelo['compartidos']:
        cantidad += f"\n{modelo['compartidos']} compartido(s)"
    uso = [f"{modelo['horas']:,.2f} h acumuladas" if modelo['horas'] else 'Sin horas acreditadas']
    for semestre in modelo['uso_semestres']:
        if not semestre['horas'] and not semestre['sesiones']:
            continue
        sesiones = ('sesiones sin total verificable' if semestre['sesiones'] is None else f"{semestre['sesiones']} sesiones")
        uso.append(f"{semestre['periodo']}: {sesiones}; {semestre['horas']:,.2f} h")
    if modelo['uso_pendiente']:
        uso.append(f"{modelo['uso_pendiente']} cierre(s) por verificar")
    pendientes = []
    if modelo['incidencias_abiertas']:
        pendientes.append(f"{modelo['incidencias_abiertas']} incidencia(s) abierta(s)")
    if modelo['mantenimiento_pendiente']:
        pendientes.append(f"{modelo['mantenimiento_pendiente']} mantenimiento(s) pendiente(s)")
    tecnica = ('; '.join(pendientes) or 'Sin pendientes técnicos') + '.\n' + _texto_vida_util(modelo['vida_util'])
    return [modelo['nombre'] + '\n' + modelo['estado'], cantidad, '\n'.join(uso), tecnica]


def bloques_estado_equipos(resumen):
    """Bloques PDF compactos para presentar qué existe antes de justificar compras."""
    bloques = [dict(tipo='parrafo', titulo='Estado de los equipos existentes por área',
        texto=f"Captura de inventario y operación al {resumen['fecha'] or 'corte no identificado'}. "
        'Incluye todas las áreas, también aquellas sin compras solicitadas. Cada activo se cuenta una vez en su área principal; '
        'los compartidos se identifican sin duplicarlos. No disponible no equivale a avería.')]
    if not resumen['disponible']:
        bloques.append(dict(tipo='vacio', texto='La captura no contiene el inventario de equipos; no se deducen existencias ni estados actuales.'))
        return bloques
    totales = resumen['totales']
    bloques.append(dict(tipo='pares', titulo='Equipos registrados en la unidad', pares=[
        ('Activos vigentes', str(totales['vigentes'])), ('Bajas registradas', str(totales['bajas'])),
        ('Registros inactivos sin baja', str(totales['inactivos'])),
        ('Incidencias abiertas / mantenimientos pendientes', f"{totales['incidencias_abiertas']} / {totales['mantenimiento_pendiente']}"),
    ]))
    if resumen['areas']:
        bloques.append(dict(tipo='tabla', titulo='Resumen del estado por área',
            anchos_relativos=[.29, .12, .30, .29],
            cabecera=['Área', 'Activos vigentes', 'Condición registrada', 'Seguimiento técnico'],
            filas=[[a['nombre'] + ('\nÁrea inactiva' if a['activa'] is False else ''), str(a['vigentes']),
                '; '.join(f"{e['nombre']}: {e['cantidad']}" for e in a['estados']) or 'Sin activos vigentes asignados',
                f"{a['incidencias_abiertas']} incidencia(s) abierta(s); {a['mantenimiento_pendiente']} mantenimiento(s) pendiente(s)"]
                for a in resumen['areas']]))
    for area in resumen['areas']:
        if area['modelos']:
            bloques.append(dict(tipo='tabla', titulo='Equipos existentes · ' + area['nombre'],
                anchos_relativos=[.32, .12, .24, .32],
                cabecera=['Modelo y condición', 'Cantidad', 'Uso acreditado', 'Control técnico y vida útil'],
                filas=[_fila_estado_modelo(m) for m in area['modelos']]))
    for clave, titulo in (('modelos_baja', 'Bajas registradas'), ('modelos_inactivos', 'Registros inactivos sin baja')):
        filas = [[a['nombre'], m['nombre'], m['estado'], str(m['cantidad'])] for a in resumen['areas'] for m in a[clave]]
        if filas:
            bloques.append(dict(tipo='tabla', titulo=titulo + ' · fuera del conteo de activos vigentes',
                cabecera=['Área capturada', 'Modelo', 'Estado registrado', 'Cantidad'], filas=filas))
    bloques.append(dict(tipo='parrafo', texto='La vida útil por fecha es una referencia de calendario y no equivale a desgaste u obsolescencia. '
        'Alcanzar una referencia de horas exige verificar la condición técnica. Las horas se acumulan por activo y no miden ocupación del área; '
        'cero horas acreditadas no demuestra desuso. La equivalencia técnica y la necesidad de compra requieren su justificación.'))
    if resumen['cierres_pendientes'] or totales['uso_pendiente']:
        bloques.append(dict(tipo='parrafo', titulo='Uso pendiente de comprobar',
            texto=f"{resumen['cierres_pendientes']} registro(s) de cierre con recursos por identificar; "
            f"{totales['uso_pendiente']} cierre(s) con uso de activos por verificar. Estas cifras pueden coincidir y no se suman. "
            'Complete los cierres antes de concluir falta de uso o capacidad.'))
    for aviso in resumen['avisos']:
        bloques.append(dict(tipo='parrafo', texto=aviso))
    return bloques


def respaldo_compras(lectura, contenido):
    fuentes = lectura.get('fuentes') or {}
    equipos = fuentes.get('equipos') or []
    por_id = {str(e['id']): e for e in equipos}
    areas, evidencias, vistos = OrderedDict(), OrderedDict(), set()
    for numero, necesidad in enumerate(contenido.get('compras') or [], 1):
        if not isinstance(necesidad, dict) or not str(necesidad.get('item') or '').strip():
            continue
        clave = str(necesidad.get('area_id') or 'pendiente')
        nombre = necesidad.get('area_nombre') or ('Toda la unidad' if clave == 'unidad' else 'Área por confirmar')
        area = areas.setdefault(clave, dict(id=clave, nombre=nombre, necesidades=[], equipos=[], modelos=[]))
        area['necesidades'].append(numero)
        for equipo_id in necesidad.get('equipos_referencia') or []:
            equipo = por_id.get(str(equipo_id))
            if equipo and equipo['id'] not in {e['id'] for e in area['equipos']}:
                area['equipos'].append(equipo)
            if equipo and equipo['id'] not in vistos:
                vistos.add(equipo['id'])
                clave_fuente = equipo.get('area_principal_id')
                evidencia = evidencias.setdefault(clave_fuente, dict(id=clave_fuente,
                    nombre=equipo.get('area_principal_nombre') or 'Sin área asignada', equipos=[], modelos=[]))
                evidencia['equipos'].append(equipo)
    for area in areas.values():
        actuales = [e for e in equipos if e.get('activo') and not e.get('baja') and (
            area['id'] == 'unidad' or str(e.get('area_principal_id', '')) == area['id'])]
        area['equipos_actuales'] = len(actuales)
        area['equipos_relacionados'] = len(area['equipos'])
        area['incidencias_abiertas'] = sum(1 for f in fuentes.get('reparaciones') or [] if
            area['id'] == 'unidad' or str((por_id.get(str(f['equipo_id'])) or {}).get('area_principal_id', '')) == area['id'])
    for area in evidencias.values():
        modelos = OrderedDict()
        for equipo in area['equipos']:
            clave_modelo = equipo.get('modelo_id') or equipo['nombre']
            modelo = modelos.setdefault(clave_modelo, dict(nombre=equipo['nombre'], equipos=[], estados=Counter()))
            modelo['equipos'].append(equipo)
            modelo['estados'][equipo.get('estado_label', equipo['estado'])] += 1
        for modelo in modelos.values():
            modelo['cantidad'] = len(modelo['equipos'])
            modelo['condicion'] = '; '.join(f'{k}: {v}' for k, v in modelo.pop('estados').items())
            modelo['horas'] = round(sum((e.get('desgaste') or {}).get('horas_documentadas', 0)
                                        for e in modelo['equipos']), 2)
            modelo['incidencias'] = sum(len(e.get('incidencias') or []) for e in modelo['equipos'])
            modelo['mantenimientos'] = sum(len(e.get('mantenimientos') or []) for e in modelo['equipos'])
            modelo['codigos'] = ', '.join(e['codigo'] for e in modelo['equipos'])
        area['modelos'] = list(modelos.values())
    return dict(areas=list(areas.values()), evidencias=list(evidencias.values()), fecha=lectura['fecha_corte'],
        necesidades=sum(len(a['necesidades']) for a in areas.values()),
        cierres_pendientes=len(fuentes.get('uso_recursos_pendiente') or []))


def bloques_respaldo_compras(respaldo):
    bloques = [dict(tipo='parrafo', titulo='Fuentes de la justificación',
        texto=f"Respaldo de las necesidades al {respaldo['fecha']}. El inventario, las incidencias y el "
        'mantenimiento se consultan como evidencia; no son cantidades que se solicitan comprar.')]
    if not respaldo['areas']:
        bloques.append(dict(tipo='vacio', titulo='Áreas relacionadas',
            texto='Registra las compras solicitadas para relacionarlas con los recursos y necesidades de cada área.'))
        return bloques
    bloques.append(dict(tipo='tabla', titulo='Áreas que sustentan la solicitud',
        cabecera=['Área de destino', 'Necesidades solicitadas', 'Activos vigentes del área', 'Incidencias abiertas'],
        filas=[[a['nombre'], str(len(a['necesidades'])), str(a['equipos_actuales']), str(a['incidencias_abiertas'])]
               for a in respaldo['areas']]))
    for area in respaldo['evidencias']:
        if not area['modelos']:
            continue
        bloques.append(dict(tipo='tabla', titulo='Recursos relacionados · ' + area['nombre'],
            cabecera=['Modelo y activos relacionados', 'Condición', 'Uso acreditado', 'Fuentes técnicas'],
            filas=[[m['nombre'] + '\n' + m['codigos'], m['condicion'], f"{m['horas']:,.2f} h",
                f"{m['incidencias']} incidencia(s); {m['mantenimientos']} mantenimiento(s)."] for m in area['modelos']]))
    if respaldo['cierres_pendientes']:
        bloques.append(dict(tipo='parrafo', texto='Hay cierres con recursos pendientes de identificar. '
            'La falta de horas acreditadas no prueba falta de uso; debe completarse el registro.'))
    return bloques
