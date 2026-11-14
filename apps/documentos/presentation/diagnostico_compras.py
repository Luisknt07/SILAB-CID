"""Diagnóstico trazable para solicitar bienes y servicios según la unidad.

El uso compara semestres completos anteriores a la elaboración. La edad de
un activo no mide desgaste; una ficha referencial sin vínculo no acredita
una falta de dotación. Las propuestas siempre requieren revisión de la unidad.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, datetime
import json

from django.db.models import Q
from django.utils import timezone


VERSION = 1


def _fecha_local_registro(instante):
    """Misma fecha institucional que el filtro ORM ``__date`` de la captura."""
    return (timezone.localtime(instante) if timezone.is_aware(instante) else instante).date().isoformat()


def semestres_cerrados(fecha, cantidad=2):
    """Los semestres naturales anteriores; el día de cierre aún no está cerrado."""
    candidatos = []
    for anio in range(max(1, fecha.year - 2), fecha.year + 1):
        for corte, inicio, fin in (('A', date(anio, 1, 1), date(anio, 6, 30)),
                                  ('B', date(anio, 7, 1), date(anio, 12, 31))):
            if fin < fecha:
                candidatos.append(dict(anio=anio, corte=corte, inicio=inicio.isoformat(), fin=fin.isoformat(),
                    etiqueta=f'{anio}-{corte}', nombre=f'{"Enero–junio" if corte == "A" else "Julio–diciembre"} {anio}'))
    return sorted(candidatos, key=lambda p: p['fin'], reverse=True)[:cantidad]


def _fecha(documento, hoy):
    fecha = hoy or timezone.localdate()
    if isinstance(fecha, datetime):
        fecha = timezone.localtime(fecha).date() if timezone.is_aware(fecha) else fecha.date()
    if hoy is None and getattr(documento, 'estado', '') == 'validado':
        emision = getattr(documento, '_constancia_qr', None)
        instante = (getattr(emision, 'emitido_en', None) or getattr(documento, 'generado_en', None)
                    or getattr(documento, 'validado_en', None))
        if instante:
            emitida = timezone.localtime(instante).date() if timezone.is_aware(instante) else instante.date()
            fecha = min(fecha, emitida)
    return fecha


def _resumen_uso(entradas):
    """Horas de ocupación: une intervalos simultáneos, no suma horas duplicadas."""
    from apps.recursos.presentation.capacidad_uso import longitud
    dias, ids = defaultdict(list), set()
    for identificador, fecha, inicio, fin in entradas:
        dias[fecha].append((inicio, fin))
        ids.add(identificador)
    return dict(sesiones=len(ids), horas=round(sum(longitud(v) for v in dias.values()) / 3600, 2),
                reservas=sorted(ids))


def _entradas_reales(reservas, fecha):
    from apps.recursos.presentation.utilizacion import _execution_values, _registrada_al_corte
    entradas = []
    for reserva in reservas:
        if not reserva.es_efectiva or reserva.fecha > fecha or not _registrada_al_corte(reserva, fecha):
            continue
        valores = _execution_values(reserva)
        if valores is not None and valores[2] > 0:
            entradas.append((reserva, valores[0], valores[1]))
    return entradas


def _espacios_reales(reserva, area_ids):
    """Sólo una identidad conservada en el cierre acredita uso de un área."""
    detalle = reserva.detalle_ejecucion if isinstance(reserva.detalle_ejecucion, dict) else {}
    captura = detalle.get('espacios')
    if not isinstance(captura, list):
        return dict(ids=[], pendientes=True, motivos=['Cierre sin espacios reales capturados'])
    ids, motivos = set(), []
    for item in captura:
        try:
            valor = item.get('id') if isinstance(item, dict) else None
            identificador = int(valor)
            if isinstance(valor, bool) or identificador <= 0 or str(identificador) != str(valor).strip():
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            motivos.append('Espacio real sin ID válido')
            continue
        if identificador not in area_ids:
            motivos.append('El espacio real no está identificado entre las áreas de esta unidad')
        else:
            ids.add(identificador)
    return dict(ids=sorted(ids), pendientes=bool(motivos), motivos=list(dict.fromkeys(motivos)))


def _repartir_uso(entradas, equipos, area_ids, periodos, *, incidencias_uso=None):
    from apps.recursos.presentation.uso_equipos import equipos_reales_reserva
    propios = {equipo.pk for equipo in equipos}
    area_uso, equipo_uso, acumulado = defaultdict(list), defaultdict(list), defaultdict(list)
    for reserva, inicio, fin in entradas:
        dato = (reserva.pk, reserva.fecha, inicio, fin)
        captura_equipos = equipos_reales_reserva(reserva)
        seleccionados = propios.intersection(captura_equipos['ids']) if not captura_equipos['pendientes'] else set()
        for equipo_id in seleccionados:
            acumulado[equipo_id].append(dato)
        captura_areas = _espacios_reales(reserva, area_ids)
        propias = (set(captura_areas['ids']) or {0}) if not captura_areas['pendientes'] else set()
        if incidencias_uso is not None:
            for recurso, captura in (('equipos', captura_equipos), ('espacios', captura_areas)):
                if captura['pendientes']:
                    incidencias_uso.append(dict(reserva=reserva.pk, fecha=reserva.fecha.isoformat(),
                        recurso=recurso, motivos=deepcopy(captura['motivos']),
                        lectura='Uso por recurso pendiente de verificar; la solicitud no acredita ejecución.'))
        for periodo in periodos:
            if periodo['inicio'] <= reserva.fecha.isoformat() <= periodo['fin']:
                for area_id in propias:
                    area_uso[(area_id, periodo['etiqueta'])].append(dato)
                for equipo_id in seleccionados:
                    equipo_uso[(equipo_id, periodo['etiqueta'])].append(dato)
    return area_uso, equipo_uso, acumulado


def _uso_global_equipos(equipos, periodos, fecha):
    """El uso de un activo prestado o compartido acompaña su identidad física."""
    from apps.recursos.presentation.uso_equipos import leer_uso_equipos
    codigos = {e.codigo_unidad for e in equipos}
    lectura = leer_uso_equipos(date.min, codigos, hasta=fecha) if codigos else {'equipos': {}}
    por_semestre, acumulado, fuentes = defaultdict(list), defaultdict(list), {}
    for equipo in equipos:
        fuente = lectura['equipos'].get(equipo.codigo_unidad) or {}
        fuentes[equipo.pk] = fuente
        for registro in fuente.get('fuentes') or []:
            fecha_uso = date.fromisoformat(registro['fecha'])
            dato = (registro['reserva_id'], fecha_uso, registro['inicio'], registro['fin'])
            acumulado[equipo.pk].append(dato)
            for periodo in periodos:
                if periodo['inicio'] <= registro['fecha'] <= periodo['fin']:
                    por_semestre[(equipo.pk, periodo['etiqueta'])].append(dato)
    return por_semestre, acumulado, fuentes


def _diagnostico_equipo(equipo, area_ids, periodos, uso, acumulado, incidencias, mantenimientos, *, fuente_uso=None, fecha=None):
    horas = _resumen_uso(acumulado.get(equipo.pk, []))
    limite = equipo.vida_util_por_horas
    familia = equipo.equipo.familia
    fin_garantia = equipo.fin_garantia
    return dict(id=equipo.pk, modelo_id=equipo.equipo_id, codigo=equipo.codigo_unidad, nombre=equipo.equipo.nombre,
        familia_id=equipo.equipo.familia_id, familia_nombre=familia.nombre if familia else '',
        estado=equipo.estado_unidad, estado_label=equipo.get_estado_unidad_display(),
        activo=equipo.activa, baja=equipo.fecha_baja.isoformat() if equipo.fecha_baja else None,
        motivo_baja=equipo.motivo_baja, reemplazo=equipo.reemplazado_por_id,
        areas_ids=sorted(area_ids), compartido=len(area_ids) > 1,
        uso_semestres=[dict(periodo=p['etiqueta'], **_resumen_uso(uso.get((equipo.pk, p['etiqueta']), []))) for p in periodos],
        uso_fuentes=deepcopy((fuente_uso or {}).get('fuentes') or []),
        uso_pendiente=deepcopy((fuente_uso or {}).get('pendientes') or []),
        desgaste=dict(horas_documentadas=horas['horas'], reservas=horas['reservas'],
            limite_horas=limite or None,
            porcentaje_referencia=round(horas['horas'] * 100 / limite, 1) if limite else None,
            lectura=('Uso documentado frente a la referencia de horas; requiere diagnóstico de condición física.'
                     if limite else 'Sin referencia por horas para medir consumo de vida útil; la edad no acredita desgaste.')),
        vida_util_referencia_fin=equipo.fin_vida_util.isoformat() if equipo.fin_vida_util else None,
        garantia=dict(fin=fin_garantia.isoformat() if fin_garantia else None,
            vigente=equipo.en_garantia(fecha), cobertura=equipo.garantia_cobertura, contacto=equipo.garantia_contacto),
        incidencias=deepcopy(incidencias.get(equipo.pk, [])),
        mantenimientos=deepcopy(mantenimientos.get(equipo.pk, [])))


def _propuestas_equipo(equipo, lectura, nombres_areas, fecha):
    areas = lectura['areas_ids']
    nombre_area = ' · '.join(nombres_areas[a] for a in areas) if areas else 'Sin área asignada'
    motivos, tipo, categoria, prioridad, accion = [], 'reposicion', 'equipos', 'media', 'Revisar reposición'
    if equipo.fecha_baja and equipo.fecha_baja > fecha:
        return []
    if equipo.fecha_baja and not equipo.reemplazado_por_id and equipo.motivo_baja in (
            'obsolescencia', 'vida_util', 'dano_irreparable', 'perdida'):
        motivos.append(f'Baja registrada el {equipo.fecha_baja:%d/%m/%Y}: {equipo.get_motivo_baja_display()}. '
                       'No tiene sustituto registrado; confirme la necesidad de reponer su función.')
    elif equipo.activa and equipo.estado_unidad == 'obsoleto':
        motivos.append('El inventario declara obsolescencia técnica. Confirme funcionalidad, prestaciones requeridas '
                       'y alternativa de renovación con respaldo técnico.')
    elif equipo.activa and not equipo.fecha_baja and equipo.estado_unidad == 'dañado':
        tipo, categoria, accion = 'mantenimiento', 'mantenimiento', 'Comparar reparación, garantía y reposición'
        motivos.append(f'Estado registrado: {equipo.get_estado_unidad_display()}. Compare diagnóstico, garantía '
                       'y reparación antes de decidir una reposición.')
    elif (equipo.activa and not equipo.fecha_baja and lectura['desgaste']['limite_horas']
          and lectura['desgaste']['horas_documentadas'] >= lectura['desgaste']['limite_horas']):
        motivos.append('Las horas de ejecución documentadas alcanzan la referencia de vida útil por horas. '
                       'Verifique la condición técnica antes de definir renovación o mantenimiento.')
    if not motivos:
        return []
    if equipo.criticidad == 'critico':
        prioridad = 'alta'
    return [dict(clave=f'diagnostico-equipo:{equipo.pk}', equipo_id=equipo.pk,
        equipos_referencia=[equipo.pk], equipo_referencia=equipo.codigo_unidad,
        codigo_equipo=equipo.codigo_unidad, area_id=areas[0] if len(areas) == 1 else 'unidad',
        area_clave=str(areas[0]) if len(areas) == 1 else 'unidad', areas_ids=areas,
        area_label=nombre_area, area_nombre=nombre_area, area=nombre_area, tipo_necesidad=tipo, categoria=categoria,
        item='Servicio de diagnóstico técnico' if tipo == 'mantenimiento' else equipo.equipo.nombre,
        clase_bien='servicios' if tipo == 'mantenimiento' else 'equipos',
        especificaciones=('Evaluar condición y alternativa de reparación del activo ' + equipo.codigo_unidad
                          if tipo == 'mantenimiento' else ''), motivo=' '.join(motivos),
        prioridad=prioridad, accion=accion, requiere_atencion=prioridad == 'alta',
        referencia=str(equipo.valor_referencial) if equipo.valor_referencial is not None else None,
        origen='inventario_y_registros_tecnicos', fuentes=dict(equipo=lectura),
        url_equipo='')]


def _brechas_capacidad(unidad, fecha):
    from apps.gestion_unidades.models.operaciones import CapacidadOperativaUnidad
    capacidad = CapacidadOperativaUnidad.objects.filter(unidad=unidad, activo=True,
        vigente_desde__lte=fecha).filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=fecha)).order_by('-vigente_desde', '-pk').first()
    if capacidad is None:
        return [], None
    fuente = dict(id=capacidad.pk, desde=capacidad.vigente_desde.isoformat(),
        hasta=capacidad.vigente_hasta.isoformat() if capacidad.vigente_hasta else None,
        aforo=capacidad.aforo_seguridad, mobiliario=capacidad.puestos_mobiliario,
        equipos=capacidad.puestos_equipados, personal=capacidad.capacidad_personal,
        fundamento=capacidad.fuente, observaciones=capacidad.observaciones)
    puestos = min(capacidad.aforo_seguridad, capacidad.puestos_mobiliario, capacidad.capacidad_personal)
    brecha = max(0, puestos - capacidad.puestos_equipados)
    if not brecha or not capacidad.fuente.strip():
        return [], fuente
    motivo = (f'La capacidad declarada y respaldada registra {capacidad.puestos_equipados} puestos equipados '
              f'frente a {puestos} puestos cubiertos por aforo, mobiliario y personal: brecha de {brecha} puestos. '
              f'Fundamento: {capacidad.fuente}. Determine qué dotación concreta hace falta; los puestos no equivalen '
              'automáticamente a unidades de equipo que deban comprarse.')
    return [dict(clave=f'capacidad:{capacidad.pk}', area_id='unidad', area_clave='unidad', areas_ids=[],
        area_label='Toda la unidad', area_nombre='Toda la unidad', area='Toda la unidad', tipo_necesidad='dotacion', categoria='equipos',
        equipos_referencia=[], equipo_referencia='', equipo_id=None, codigo_equipo='',
        item='', titulo='Dotación para cubrir la brecha operativa documentada', requiere_nombre_bien=True,
        clase_bien='equipos', motivo=motivo,
        prioridad='media', accion='Precisar la dotación y justificar su incorporación',
        requiere_atencion=False, referencia=None, origen='capacidad_operativa_declarada',
        fuentes=dict(capacidad=fuente), url_equipo='')], fuente


def _propuestas_insumos(unidad, relaciones, nombres_areas):
    from apps.recursos.models.consumibles import Consumible
    from .diagnostico_existencias import clase_existencia
    propuestas, lecturas = [], []
    for insumo in Consumible.objects.filter(unidad=unidad, activo=True).order_by('pk'):
        areas = sorted(relaciones.get(insumo.pk, []))
        lectura = dict(id=insumo.pk, codigo=insumo.codigo, nombre=insumo.nombre,
            stock=str(insumo.stock_total), minimo=str(insumo.minimo), seguridad=str(insumo.stock_seguridad),
            estado=insumo.estado_stock, unidad_medida=insumo.unidad_medida, areas_ids=areas,
            clase_bien=clase_existencia(insumo.clasificacion), clasificacion=insumo.clasificacion)
        lecturas.append(lectura)
        if insumo.estado_stock not in ('agotado', 'critico'):
            continue
        motivo = (f'El inventario registra {insumo.stock_total} {insumo.unidad_medida or "unidades"} '
                  f'y estado {insumo.estado_stock}. Confirme el conteo, el consumo previsto y las compras '
                  'o entregas pendientes antes de definir la cantidad a reponer.')
        nombre_area = ' · '.join(nombres_areas[a] for a in areas) if areas else 'Sin área asignada'
        propuestas.append(dict(clave=f'diagnostico-insumo:{insumo.pk}', equipo_id=None,
            equipos_referencia=[], equipo_referencia='', codigo_equipo='',
            area_id=areas[0] if len(areas) == 1 else 'unidad',
            area_clave=str(areas[0]) if len(areas) == 1 else 'unidad',
            areas_ids=areas, area_label=nombre_area, area_nombre=nombre_area, area=nombre_area, tipo_necesidad='insumos', categoria='insumos',
            item=insumo.nombre, clase_bien=clase_existencia(insumo.clasificacion),
            unidad_medida=insumo.unidad_medida or '', especificaciones=insumo.especificacion_tecnica,
            motivo=motivo, prioridad='alta' if insumo.estado_stock == 'agotado' else 'media',
            accion='Revisar reposición de existencias', requiere_atencion=insumo.estado_stock == 'agotado',
            referencia=None, origen='existencias_registradas', fuentes=dict(insumo=lectura), url_equipo=''))
    return propuestas, lecturas


def diagnostico_unidad(documento, hoy=None):
    """Consulta fuentes reales; devuelve datos JSON sin crear ni modificar registros."""
    from apps.gestion_unidades.models.espacios import EspacioReservable
    from apps.gestion_unidades.models.fichas_area import ElementoFichaArea
    from apps.recursos.models.mantenimiento import IncidenciaEquipo, MantenimientoEquipo
    from apps.recursos.models.unidades import UnidadEquipo
    from apps.reservas.models.reservas import Reserva
    from apps.recursos.presentation.utilizacion import calculate_unit_utilization

    fecha, unidad = _fecha(documento, hoy), documento.unidad
    periodos = semestres_cerrados(fecha)
    espacios = list(EspacioReservable.objects.filter(unidad=unidad).select_related('ficha')
                    .prefetch_related('equipos_asociados').order_by('orden', 'nombre', 'pk'))
    equipos = list(UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad))
        .filter(Q(activa=True) | Q(fecha_baja__isnull=False)).distinct()
        .select_related('equipo__familia').prefetch_related('codigos_anteriores', 'espacios_asociados').order_by('codigo_unidad'))
    por_id = {e.pk: e for e in equipos}
    areas_equipo = defaultdict(set)
    for espacio in espacios:
        for equipo in espacio.equipos_asociados.all():
            if equipo.pk in por_id:
                areas_equipo[equipo.pk].add(espacio.pk)
    reservas = Reserva.objects.filter(laboratorio=unidad, fecha__lte=fecha,
        estado='completada', resultado_cierre='atendida')
    entradas = _entradas_reales(reservas, fecha)
    incidencias_uso = []
    areas_uso, equipos_uso, acumulado = _repartir_uso(entradas, equipos, {a.pk for a in espacios}, periodos,
                                                  incidencias_uso=incidencias_uso)
    # Áreas y actividad de la unidad permanecen locales. La condición y el
    # desgaste del activo consideran su ejecución en cualquier unidad, incluso
    # durante préstamos o después de cambios de adscripción.
    equipos_uso, acumulado, fuentes_uso = _uso_global_equipos(equipos, periodos, fecha)
    # El historial técnico acompaña la identidad física, también cuando la
    # incidencia o la orden se registró durante un préstamo o uso compartido.
    # No se atribuyen aquí esos costes ni su cumplimiento a esta unidad.
    alcance = Q(equipo_id__in=por_id)
    incidencias, mantenimientos = defaultdict(list), defaultdict(list)
    for registro in IncidenciaEquipo.objects.filter(alcance, fecha_reporte__date__lte=fecha).order_by('fecha_reporte', 'pk'):
        incidencias[registro.equipo_id].append(dict(id=registro.pk, fecha=_fecha_local_registro(registro.fecha_reporte),
            tipo=registro.tipo, estado=registro.estado, titulo=registro.titulo, descripcion=registro.descripcion,
            detiene_operacion=registro.detiene_operacion, solucion=registro.solucion))
    for registro in MantenimientoEquipo.objects.filter(alcance, fecha_programada__date__lte=fecha).order_by('fecha_programada', 'pk'):
        mantenimientos[registro.equipo_id].append(dict(id=registro.pk, codigo=registro.codigo, tipo=registro.tipo,
            estado=registro.estado, programado=_fecha_local_registro(registro.fecha_programada),
            terminado=_fecha_local_registro(registro.fecha_fin) if registro.fecha_fin else None,
            titulo=registro.titulo, resultado=registro.resultado, costo=str(registro.costo) if registro.costo is not None else None))
    lecturas = {e.pk: _diagnostico_equipo(e, areas_equipo[e.pk], periodos, equipos_uso, acumulado,
                                        incidencias, mantenimientos, fuente_uso=fuentes_uso.get(e.pk), fecha=fecha) for e in equipos}
    from apps.recursos.presentation.areas_recursos import asignaciones_por_area
    asignacion = asignaciones_por_area(unidad, equipos, espacios)
    for equipo_id, area in asignacion['por_equipo'].items():
        lecturas[equipo_id].update(area_principal_id=area['area_id'], area_principal_nombre=area['area_nombre'],
            areas_compartidas_ids=[a.pk for a in area['areas_compartidas']])
    from django.urls import reverse
    for lectura in lecturas.values():
        lectura['url'] = reverse('ficha_equipo_publica', args=[unidad.slug, lectura['codigo']])
    nombres = {a.pk: a.nombre for a in espacios}
    propuestas = [p for e in equipos for p in _propuestas_equipo(e, lecturas[e.pk], nombres, fecha)]
    from .compras_reparacion import propuestas_reparacion
    diagnosticadas, reparaciones = propuestas_reparacion(unidad, equipos, nombres, areas_equipo, fecha)
    con_decision = {p['equipo_id'] for p in diagnosticadas}
    propuestas = [p for p in propuestas if p.get('equipo_id') not in con_decision] + diagnosticadas
    brechas, capacidad = _brechas_capacidad(unidad, fecha)
    propuestas.extend(brechas)
    referencias, dotacion = defaultdict(list), defaultdict(list)
    areas_insumos, areas_software = defaultdict(set), defaultdict(set)
    for elemento in ElementoFichaArea.objects.filter(ficha__espacio__unidad=unidad,
            tipo__in=('equipo', 'software', 'insumo')).select_related('ficha').order_by('pk'):
        enlace = {'equipo': elemento.registrado_id, 'software': elemento.software_registrado_id,
                  'insumo': elemento.insumo_registrado_id}[elemento.tipo]
        dotacion[elemento.ficha.espacio_id].append(dict(id=elemento.pk, tipo=elemento.tipo,
            nombre=elemento.nombre, nivel=elemento.nivel, cantidad_referencial=elemento.cantidad,
            para_que=elemento.para_que, especificaciones=elemento.especificaciones,
            solo_referencia=elemento.solo_referencia,
            registrado_id=elemento.registrado_id, software_registrado_id=elemento.software_registrado_id,
            insumo_registrado_id=elemento.insumo_registrado_id,
            fuente=elemento.url or elemento.ficha.fuente, ficha_id=elemento.ficha_id, origen='ficha_area'))
        if elemento.tipo == 'insumo' and enlace:
            areas_insumos[enlace].add(elemento.ficha.espacio_id)
        if elemento.tipo == 'software' and enlace:
            areas_software[enlace].add(elemento.ficha.espacio_id)
        if not enlace:
            referencias[elemento.ficha.espacio_id].append(dict(id=elemento.pk, tipo=elemento.tipo,
                nombre=elemento.nombre, cantidad_referencial=elemento.cantidad,
                lectura='Referencia de la ficha sin vínculo al inventario: confirmar existencia, no implica compra.'))
    # Un proceso identifica una función y un modelo; no fija cuántos activos
    # hacen falta ni acredita que una receta de referencia ya esté validada.
    from apps.plantas_piloto.operacion.models.produccion import EtapaReceta
    etapas = (EtapaReceta.objects.filter(receta__unidad=unidad, receta__activa=True,
            espacio__unidad=unidad, espacio__activo=True).select_related('receta', 'equipo__familia')
            .order_by('espacio_id', 'receta_id', 'orden', 'pk'))
    for etapa in etapas:
        modelo = etapa.equipo
        dotacion[etapa.espacio_id].append(dict(id=etapa.pk, origen='etapa_proceso', tipo='equipo',
            nombre=modelo.nombre if modelo else '', para_que=etapa.nombre, cantidad_referencial='',
            modelo_id=etapa.equipo_id, familia_id=modelo.familia_id if modelo else None,
            familia_nombre=modelo.familia.nombre if modelo and modelo.familia else '',
            receta_id=etapa.receta_id, receta_codigo=etapa.receta.codigo,
            receta_nombre=etapa.receta.nombre, estado_receta=etapa.receta.origen,
            fuente='Proceso ' + etapa.receta.codigo, registrado_id=None))
    propuestas_insumos, insumos = _propuestas_insumos(unidad, areas_insumos, nombres)
    propuestas.extend(propuestas_insumos)
    from .diagnostico_existencias import inventario_por_clase
    recursos_clases = inventario_por_clase(unidad, equipos, areas_equipo, areas_insumos, areas_software, nombres)
    areas = []
    for area_id, nombre in [*((a.pk, a.nombre) for a in espacios), (0, 'Sin área asignada')]:
        espacio = next((a for a in espacios if a.pk == area_id), None)
        ficha = getattr(espacio, 'ficha', None) if espacio is not None else None
        propios = [e for e in lecturas.values() if area_id in e['areas_ids'] or area_id == 0 and not e['areas_ids']]
        areas.append(dict(id=area_id, nombre=nombre,
            activa=espacio.activo if espacio else True, equipos_ids=[e['id'] for e in propios],
            funcion=(espacio.descripcion_publica or (ficha.que_es if ficha else '')) if espacio else '',
            aplicaciones=ficha.aplicaciones if ficha else '', fuente_funcion=ficha.fuente if ficha else '',
            politica_reserva=espacio.politica_reserva if espacio else '',
            capacidad_usuarios=espacio.capacidad if espacio else None,
            dotacion_referencia=dotacion[area_id],
            equipos=deepcopy(propios), estados=dict(Counter(e['estado'] for e in propios)),
            estados_legibles=dict(Counter(e['estado_label'] for e in propios)),
            equipos_compartidos=sum(e['compartido'] for e in propios),
            insumos=[i for i in insumos if area_id in i['areas_ids'] or area_id == 0 and not i['areas_ids']],
            uso_semestres=[dict(periodo=p['etiqueta'], **_resumen_uso(areas_uso.get((area_id, p['etiqueta']), []))) for p in periodos],
            referencias_sin_vinculo=referencias[area_id],
            faltantes_documentados=[],
            sugerencias=[p['clave'] for p in propuestas if area_id in p['areas_ids'] or
                         area_id == 0 and not p['areas_ids'] and p['origen'] != 'capacidad_operativa_declarada']))
    usos = []
    for periodo in periodos:
        medida = calculate_unit_utilization(unidad, date.fromisoformat(periodo['inicio']),
            date.fromisoformat(periodo['fin']), hoy=fecha)
        usos.append(dict(periodo=periodo['etiqueta'], nombre=periodo['nombre'],
            horas_efectivas=medida['occupied_hours'], horas_disponibles=medida['theoretical_hours'],
            atenciones=medida['effective_attentions'], utilizacion=medida['utilization'],
            frecuencia=medida['frequency'], pendiente=medida['pending'], calidad=medida['quality'],
            alertas=medida['alertas'], fuentes_medicion=medida['fuentes_medicion']))
    resultado = dict(version=VERSION, unidad=unidad.pk, anio=documento.anio, fecha_corte=fecha.isoformat(),
        periodos=periodos, inventario=dict(equipos_unicos=sum(e.activa and not e.fecha_baja for e in equipos),
            estados=dict(Counter(e.estado_unidad for e in equipos if e.activa and not e.fecha_baja)),
            equipos_ids=sorted(e.pk for e in equipos if e.activa and not e.fecha_baja)), uso_semestres=usos, areas=areas, sugerencias=propuestas,
        faltantes_documentados=brechas, recursos_clases=recursos_clases, asignacion_areas_version=1,
        contraste_areas_version=1,
        fuentes=dict(capacidad=capacidad, equipos=[lecturas[k] for k in sorted(lecturas)], insumos=insumos,
            reparaciones=reparaciones,
            uso_equipos_ambito='global_por_activo',
            uso_recursos_pendiente=incidencias_uso,
            areas=[dict(id=a.pk, nombre=a.nombre, activa=a.activo) for a in espacios]),
        alcance='Diagnóstico de registros para revisión; no certifica financiación ni obliga a adquirir recursos.')
    return json.loads(json.dumps(resultado, ensure_ascii=False, default=str))


def lectura_diagnostico(documento, contenido, hoy=None):
    captura = contenido.get('diagnostico_compras_fuentes') if isinstance(contenido, dict) else None
    requiere_fuente_actual = bool(isinstance(contenido, dict) and contenido.get('compras_resumen_version') == 1
        and getattr(documento, 'estado', '') not in ('validado', 'cargado')
        and isinstance(captura, dict) and (captura.get('asignacion_areas_version') != 1
                                         or captura.get('contraste_areas_version') != 1))
    if (isinstance(captura, dict) and captura.get('version') == VERSION
            and captura.get('unidad') == documento.unidad_id and captura.get('anio') == documento.anio
            and isinstance(captura.get('areas'), list) and not requiere_fuente_actual):
        return deepcopy(captura)
    return diagnostico_unidad(documento, hoy=hoy)


def fijar_diagnostico(documento, contenido, hoy=None, actualizar=False):
    resultado = deepcopy(contenido) if isinstance(contenido, dict) else {}
    if actualizar:
        resultado.pop('diagnostico_compras_fuentes', None)
    resultado['diagnostico_compras_fuentes'] = lectura_diagnostico(documento, resultado, hoy=hoy)
    return resultado


def bloques_diagnostico(lectura, contenido=None):
    """Presentación compacta del diagnóstico para el PDF; no consulta fuentes."""
    bloques = [dict(tipo='pares', titulo='Diagnóstico para sustentar las necesidades', pares=[
        ('Fecha de referencia', lectura['fecha_corte']),
        ('Equipos únicos registrados', str(lectura['inventario']['equipos_unicos'])),
        ('Antecedente de uso', 'Últimos dos semestres de gestión cerrados antes de elaborar la propuesta'),
    ])]
    if lectura.get('recursos_clases'):
        from .diagnostico_existencias import bloques_existencias
        bloques.extend(bloques_existencias(lectura['recursos_clases']))
    filas = [[u['nombre'], str(u['atenciones']), f"{u['horas_efectivas']:,.2f}",
              'Pendiente de comprobar' if u['pendiente'] else f"{u['utilizacion']:.1f} %"] for u in lectura['uso_semestres']]
    bloques.append(dict(tipo='tabla', titulo='Uso registrado en semestres cerrados',
        cabecera=['Semestre', 'Atenciones', 'Horas efectivas', 'Utilización'], filas=filas))
    filas = []
    for area in lectura['areas']:
        etiquetas = {e['estado']: e.get('estado_label', e['estado'].replace('_', ' ').capitalize()) for e in area['equipos']}
        estados = '; '.join(f'{etiquetas.get(estado, estado.replace("_", " ").capitalize())}: {cantidad}'
                            for estado, cantidad in sorted(area['estados'].items())) or 'Sin equipos vinculados'
        uso = '; '.join(f"{u['periodo']}: {u['sesiones']} atenciones, {u['horas']:,.2f} h" for u in area['uso_semestres'])
        tecnicos = sum(len(e['incidencias']) for e in area['equipos'])
        desgaste = sum(bool(e['desgaste']['limite_horas']) and e['desgaste']['horas_documentadas'] >= e['desgaste']['limite_horas']
                       for e in area['equipos'])
        respaldo = [f'{tecnicos} incidencia(s) registrada(s)' if tecnicos else 'Sin incidencias registradas']
        if desgaste:
            respaldo.append(f'{desgaste} activo(s) alcanzan la referencia de horas')
        if area['referencias_sin_vinculo']:
            respaldo.append(f"{len(area['referencias_sin_vinculo'])} referencia(s) de ficha por vincular")
        filas.append([area['nombre'], str(len(area['equipos_ids'])), estados, uso, '. '.join(respaldo) + '.'])
    bloques.append(dict(tipo='tabla', titulo='Inventario, condición y uso por área',
        cabecera=['Área', 'Equipos', 'Estados registrados', 'Uso con área identificada', 'Respaldo técnico'], filas=filas))
    fuentes = lectura.get('fuentes') or {}
    pendientes_recursos = fuentes.get('uso_recursos_pendiente') or []
    if pendientes_recursos:
        bloques.append(dict(tipo='tabla', titulo='Cierres pendientes de identificación de recursos',
            cabecera=['Reserva / fecha', 'Recurso', 'Dato por verificar'],
            filas=[[f"#{r['reserva']} · {r['fecha']}", 'Equipos' if r['recurso'] == 'equipos' else 'Espacios',
                    '; '.join(r.get('motivos') or [])] for r in pendientes_recursos]))
        bloques.append(dict(tipo='parrafo', titulo='', texto='Las horas y atenciones por equipo o área '
            'sólo incluyen los recursos identificados en cierres reales completos. Los cierres pendientes '
            'pueden explicar un cero registrado; no se sustituyen por los equipos o espacios solicitados.'))
    nombres_areas = {a['id']: a['nombre'] for a in lectura['areas']}
    periodos = lectura.get('periodos') or []
    seleccionados = None
    if contenido is not None:
        seleccionados = {str(equipo_id) for fila in contenido.get('compras', [])
                         if isinstance(fila, dict)
                         for equipo_id in (fila.get('equipos_referencia') or [])}
    filas = []
    for equipo in fuentes.get('equipos') or []:
        if seleccionados is not None and str(equipo['id']) not in seleccionados:
            continue
        areas = ' · '.join(nombres_areas.get(i, str(i)) for i in equipo.get('areas_ids', [])) or 'Sin área asignada'
        por_semestre = {u['periodo']: u for u in equipo.get('uso_semestres', [])}
        uso = []
        for periodo in periodos:
            valor = por_semestre.get(periodo['etiqueta']) or {}
            uso.append(f"{valor.get('sesiones', 0)} atenciones · {valor.get('horas', 0):,.2f} h")
        desgaste = equipo.get('desgaste') or {}
        horas = desgaste.get('horas_documentadas', 0)
        limite = desgaste.get('limite_horas')
        respaldo = (f'{horas:,.2f} h documentadas / {limite} h de referencia. '
                    'Comprobar condición técnica.' if limite else
                    'Sin referencia por horas para valorar consumo de vida útil.')
        incidentes = equipo.get('incidencias') or []
        mantenimientos = equipo.get('mantenimientos') or []
        if incidentes:
            ultima = incidentes[-1]
            respaldo += (f" {len(incidentes)} incidencia(s). Última: #{ultima['id']} · "
                         f"{ultima['titulo']} ({ultima['estado']}).")
        if mantenimientos:
            ultimo = mantenimientos[-1]
            respaldo += (f" {len(mantenimientos)} orden(es) de mantenimiento. Última: "
                         f"{ultimo.get('codigo') or ultimo['id']} ({ultimo['estado']}).")
        if equipo.get('uso_pendiente'):
            respaldo += f" {len(equipo['uso_pendiente'])} cierre(s) con uso del activo pendiente de verificar."
        estado = equipo.get('estado_label') or equipo.get('estado', 'Sin estado registrado')
        if equipo.get('baja'):
            estado += ' · Baja: ' + equipo['baja']
        filas.append([f"{equipo['codigo']} · {equipo['nombre']}\n{areas}", estado, *uso, respaldo])
    if filas:
        titulo = ('Equipos actuales relacionados con las compras' if seleccionados is not None else
                  'Equipos únicos: estado y uso documentado por semestre')
        bloques.append(dict(tipo='tabla', titulo=titulo,
            cabecera=['Equipo y áreas', 'Estado al elaborar la propuesta',
                      *[p['nombre'] for p in periodos], 'Condición y fuentes técnicas'], filas=filas))
    if seleccionados is not None:
        bloques.append(dict(tipo='parrafo', titulo='', texto='El detalle de equipos incluye únicamente los activos '
            'seleccionados como sustento de las compras. Los resúmenes por área abarcan todo el inventario; '
            'el inventario completo se consulta en el módulo de recursos de la unidad.'))
    if fuentes.get('uso_equipos_ambito') == 'global_por_activo':
        bloques.append(dict(tipo='parrafo', titulo='', texto='El uso y las horas acumuladas de cada equipo '
            'incluyen sus cierres reales en todas las unidades, también durante préstamos. Las áreas y los '
            'indicadores de actividad de esta unidad conservan únicamente las atenciones realizadas aquí; '
            'el uso externo del activo no aumenta el cumplimiento de la unidad de origen.'))
    capacidad = fuentes.get('capacidad')
    if isinstance(capacidad, dict):
        bloques.append(dict(tipo='pares', titulo='Capacidad y dotación declaradas de la unidad', pares=[
            ('Vigencia de referencia', capacidad['desde'] + ' – ' + (capacidad.get('hasta') or 'Sin fecha final')),
            ('Aforo y seguridad', str(capacidad['aforo'])),
            ('Puestos con mobiliario', str(capacidad['mobiliario'])),
            ('Puestos equipados', str(capacidad['equipos'])),
            ('Capacidad de atención del personal', str(capacidad['personal'])),
            ('Fuente de los valores', capacidad.get('fundamento') or 'Sin fundamento registrado; requiere revisión'),
            ('Observaciones registradas', capacidad.get('observaciones') or 'Sin observaciones adicionales'),
        ]))
    for brecha in lectura.get('faltantes_documentados') or []:
        bloques.append(dict(tipo='parrafo', titulo='Brecha de dotación con fundamento registrado',
                            texto=brecha['motivo']))
    bloques.append(dict(tipo='parrafo', titulo='', texto='Un equipo compartido puede aparecer en varias áreas; '
        'el inventario de la unidad cuenta cada activo una sola vez. El uso por área sólo incluye atenciones '
        'con esa área identificada en el cierre real y no debe sumarse entre áreas compartidas. La antigüedad y las referencias '
        'sin vínculo al inventario no prueban desgaste ni una necesidad de compra. Las horas por activo o área '
        'provienen del horario real registrado; la utilización de la unidad además contrasta jornadas, '
        'asistencia y capacidad, conservando sus incidencias de calidad.'))
    return bloques
