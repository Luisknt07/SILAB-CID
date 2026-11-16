"""Anexos de resultados de investigación y de transferencia y servicios.

Tablas y columnas: docs/estructura-anexos-por-tipo-de-unidad.md, secciones 4.10 y 4.11. Cada
función recibe un :class:`~apps.documentos.presentation.anexos_evidencia.Contexto` y devuelve
la lista de :class:`~apps.documentos.presentation.anexos_evidencia.Registro` del anexo, en el
orden de la especificación. El motor numera las tablas y dibuja el PDF.
"""

from collections import defaultdict
from datetime import date

from .anexos_evidencia import (
    Registro, cifra, enlace, enlace_recurso, evidencias_de_gestion, fecha, nombre_de, par, plural, texto,
    verificacion,
)


def _detalle(evidencia):
    return evidencia.detalle if isinstance(evidencia.detalle, dict) else {}


def _tipo_producto(detalle):
    from apps.documentos.models.resultados_gestion import TIPOS_PRODUCTO
    return texto(dict(TIPOS_PRODUCTO).get(detalle.get('tipo_producto'), ''), 60)


def _respaldo(evidencia):
    return enlace_recurso(evidencia.recurso) if evidencia.recurso_id else enlace(evidencia.enlace)


def _acredita(evidencia):
    return evidencia.estado == 'validado' and not evidencia.demostracion


def _fecha_iso(valor):
    """Una fecha guardada como texto «aaaa-mm-dd», en la escritura local; '' si no es una fecha."""
    try:
        return fecha(date.fromisoformat(str(valor or '')))
    except ValueError:
        return ''


def _dinero(valor):
    return f'{cifra(valor, 2)} USD'


def _solicitante_de(reserva):
    """Quién pidió la sesión y para qué entidad: (nombre, entidad)."""
    nombre = (reserva.nombre_solicitante or '').strip() or nombre_de(reserva.usuario)
    return nombre, reserva.entidad_beneficiaria.strip() or (reserva.institucion or '').strip()


# -- investigación -------------------------------------------------------------------------

def _resultados(contexto):
    filas = []
    verificados = 0
    for evidencia in evidencias_de_gestion(contexto.unidad, 'INVESTIGACION', contexto.inicio, contexto.fin):
        detalle = _detalle(evidencia)
        verificados += _acredita(evidencia)
        filas.append([
            texto(evidencia.codigo),
            fecha(evidencia.fecha),
            texto(detalle.get('proyecto'), 100),
            _tipo_producto(detalle),
            par(texto(detalle.get('producto') or evidencia.titulo, 100), texto(evidencia.descripcion, 180)),
            nombre_de(evidencia.responsable),
            texto(detalle.get('beneficiario'), 90),
            verificacion(evidencia),
            _respaldo(evidencia),
        ])
    return Registro('Resultados',
                    ('Código', 'Fecha', 'Proyecto', 'Tipo de producto', 'Producto / resultado', 'Responsable',
                     'Beneficiario', 'Verificación', 'Respaldo'),
                    filas, pesos=(11, 8, 14, 11, 20, 10, 10, 9, 7),
                    total=f'Total: {plural(len(filas), "resultado", "resultados")} · verificados: {cifra(verificados)}',
                    vacio='No hay resultados de investigación registrados en el período.')


# Los mismos propósitos que el informe cuenta como uso para investigación.
PROPOSITOS_DE_INVESTIGACION = ('investigacion_innovacion', 'titulacion')


def _sesiones_de_investigacion(contexto):
    from apps.gestion_unidades.presentation.reportes_dimensiones import horas_efectivas
    from apps.reservas.models.reservas import Reserva
    from .expediente_redaccion import ESTADOS_RESERVA_DESCARTADOS

    filas = []
    atendidas = 0
    horas_totales = 0.0
    for reserva in (Reserva.objects.filter(laboratorio=contexto.unidad,
                                           proposito_codigo__in=PROPOSITOS_DE_INVESTIGACION,
                                           fecha__range=(contexto.inicio, contexto.fin))
                    .exclude(estado__in=ESTADOS_RESERVA_DESCARTADOS).select_related('usuario', 'actividad_catalogo')
                    .order_by('fecha', 'hora_inicio', 'pk')):
        atendida = reserva.es_efectiva
        horas = horas_efectivas(reserva) if atendida else 0.0
        atendidas += atendida
        horas_totales += horas
        actividad = reserva.referencia_actividad.strip() or (
            reserva.actividad_catalogo.nombre if reserva.actividad_catalogo_id else '') or reserva.resumen_solicitud
        responsable = reserva.responsable_actividad.strip() or _solicitante_de(reserva)[0]
        filas.append([
            texto(reserva.codigo_reserva),
            fecha(reserva.fecha),
            par(texto(actividad, 100), texto(reserva.intencion_solicitud, 200) if reserva.intencion_solicitud.strip()
                else ''),
            texto(responsable, 60),
            cifra(round(horas, 2)) if atendida else '—',
        ])
    return Registro('Uso de la unidad para investigación',
                    ('Sesión', 'Fecha', 'Proyecto o actividad', 'Responsable', 'Horas efectivas'),
                    filas, pesos=(14, 10, 46, 18, 12),
                    total=(f'Total: {plural(len(filas), "sesión", "sesiones")} · atendidas: {cifra(atendidas)} · '
                           f'horas efectivas: {cifra(round(horas_totales, 1))}'),
                    vacio='No hay sesiones de investigación registradas en el período.')


def investigacion(contexto):
    """Anexo de resultados de investigación aplicada y desarrollo tecnológico (sección 4.10).

    Los resultados documentados del período y las sesiones en que la unidad se usó para investigar.
    Una sesión es uso, no resultado: se cita por su código del anexo de registros de uso.
    """
    return [_resultados(contexto), _sesiones_de_investigacion(contexto)]


# -- transferencia y servicios -------------------------------------------------------------

def _transferencias(contexto):
    filas = []
    verificadas = aceptadas = 0
    for evidencia in evidencias_de_gestion(contexto.unidad, 'TRANSFERENCIA', contexto.inicio, contexto.fin):
        detalle = _detalle(evidencia)
        aceptada = detalle.get('aceptacion') == 'aceptado'
        verificadas += _acredita(evidencia)
        aceptadas += aceptada
        aceptacion = par(_fecha_iso(detalle.get('fecha_aceptacion')) or 'Aceptada',
                         texto(detalle.get('referencia_aceptacion'), 90)
                         if str(detalle.get('referencia_aceptacion') or '').strip() else '') if aceptada else 'Pendiente'
        filas.append([
            texto(evidencia.codigo),
            fecha(evidencia.fecha),
            texto(detalle.get('beneficiario'), 100),
            _tipo_producto(detalle),
            texto(detalle.get('producto') or evidencia.titulo, 140),
            aceptacion,
            verificacion(evidencia),
            _respaldo(evidencia),
        ])
    return Registro('Transferencias',
                    ('Código', 'Fecha', 'Entidad destinataria', 'Tipo', 'Entregable', 'Aceptación', 'Verificación',
                     'Respaldo'),
                    filas, pesos=(12, 8, 17, 13, 20, 13, 10, 7),
                    total=(f'Total: {plural(len(filas), "transferencia", "transferencias")} · '
                           f'aceptadas: {cifra(aceptadas)} · verificadas: {cifra(verificadas)}'),
                    vacio='No hay transferencias registradas en el período.')


def _fila_de_servicio(reserva, solicitud, ordenes):
    """Un servicio: la sesión reservada y, si la hay, su solicitud operativa."""
    from apps.gestion_unidades.presentation.reportes_dimensiones import horas_efectivas

    cierre = (solicitud.fecha_cierre if solicitud else None) or (reserva.fecha_cierre if reserva else None)
    if cierre:
        entrega = f'entregado {fecha(cierre)}'
    elif reserva is not None and reserva.fecha_entrega_prevista:
        entrega = f'entrega prevista {fecha(reserva.fecha_entrega_prevista)}'
    else:
        entrega = ''
    if reserva is not None:
        solicitante, entidad = _solicitante_de(reserva)
        titulo = reserva.resumen_solicitud
        descripcion = (solicitud.descripcion_general if solicitud else '') or reserva.detalle_trabajo
        modalidad = reserva.get_modalidad_servicio_display() if reserva.modalidad_servicio else ''
    else:
        solicitante = nombre_de(solicitud.solicitante)
        entidad = (solicitud.departamento or '').strip()
        titulo = solicitud.nombre_proyecto
        descripcion = solicitud.descripcion_general
        modalidad = ''
    if solicitud is not None:
        estado = par(solicitud.get_estado_display(),
                     f'sesión {reserva.get_estado_display().lower()}' if reserva is not None else '')
        # Un tipo de trabajo fuera del catálogo se muestra tal como se guardó.
        tipo_trabajo = solicitud.get_tipo_trabajo_display()
        tipo_trabajo = texto(tipo_trabajo[:1].upper() + tipo_trabajo[1:], 60)
    else:
        estado = par(reserva.get_estado_display(),
                     reserva.get_resultado_cierre_display() if reserva.resultado_cierre else '')
        tipo_trabajo = '—'
    if reserva is not None and reserva.es_efectiva:
        horas = par(cifra(round(horas_efectivas(reserva), 2)), 'efectivas')
    elif solicitud is not None and solicitud.tiempo_estimado_horas:
        horas = par(cifra(solicitud.tiempo_estimado_horas, 2), 'estimadas')
    else:
        horas = '—'
    valor = '—'
    if reserva is not None:
        finales = [f'{rotulo} {_dinero(monto)}' for rotulo, monto in (
            ('final', reserva.valor_final_usuario), ('aporte institucional', reserva.aporte_institucional_real))
            if monto is not None]
        if reserva.costo_estimado is not None or finales:
            valor = par(_dinero(reserva.costo_estimado) if reserva.costo_estimado is not None else '—',
                        ' · '.join(finales))
    sesion = (reserva.codigo_reserva or '') if reserva is not None else ''
    # La solicitud operativa no tiene código propio: sin sesión, se nombra por su número.
    codigo = sesion or ((solicitud.numero_orden or f'Solicitud {solicitud.pk}') if solicitud is not None else '')
    return [
        texto(codigo),
        par(fecha(solicitud.fecha_solicitud if solicitud else reserva.fecha), entrega),
        par(texto(solicitante, 60), texto(entidad, 90) if entidad else ''),
        par(tipo_trabajo, modalidad),
        par(texto(titulo, 100), texto(descripcion, 180) if str(descripcion or '').strip() else ''),
        estado,
        horas,
        valor,
        # Dónde quedó registrada la ejecución: la orden de producción o la sesión de uso.
        texto(', '.join(o.codigo for o in ordenes) if ordenes else sesion),
    ]


def _fila_de_maquila(orden):
    """Un procesamiento para terceros sin solicitud de servicio: se cita su orden de producción."""
    reserva = orden.reserva
    solicitante, entidad = _solicitante_de(reserva) if reserva is not None else ('', '')
    fin = f'fin {fecha(orden.fecha_fin)}' if orden.fecha_fin != orden.fecha_inicio else ''
    return [
        texto(reserva.codigo_reserva if reserva is not None else ''),
        par(fecha(orden.fecha_inicio), fin),
        par(texto(solicitante, 60), texto(entidad, 90) if entidad else ''),
        orden.get_origen_display(),
        par(texto(orden.producto.nombre, 100), texto(orden.receta.nombre, 120)),
        orden.get_estado_display(),
        '—',
        '—',
        texto(orden.codigo),
    ]


def _servicios(contexto):
    """Las solicitudes de servicio del período y, en la planta piloto, la maquila que no nació de una."""
    from django.db.models import Q

    from apps.laboratorios.operacion.models.fablab import SolicitudFabricacion
    from apps.reservas.models.reservas import Reserva
    from .expediente_redaccion import ESTADOS_RESERVA_DESCARTADOS

    unidad, inicio, fin = contexto.unidad, contexto.inicio, contexto.fin
    # Un servicio pertenece al período en que se solicitó; sin solicitud operativa, al de su sesión.
    solicitudes = list(SolicitudFabricacion.objects.filter(unidad=unidad, fecha_solicitud__range=(inicio, fin))
                       .select_related('reserva__usuario', 'solicitante'))
    sin_solicitud = list(Reserva.objects.filter(laboratorio=unidad, tipo_solicitud='servicio',
                                                fecha__range=(inicio, fin), solicitudes_operativas__isnull=True)
                         .select_related('usuario'))
    servicios = [(s.fecha_solicitud, s.pk, s.reserva, s) for s in solicitudes]
    servicios += [(r.fecha, r.pk, r, None) for r in sin_solicitud]

    def descartado(reserva, solicitud):
        if solicitud is not None and solicitud.estado == 'completada':
            return False
        if solicitud is not None and solicitud.estado == 'rechazada':
            return True
        return reserva is not None and reserva.estado in ESTADOS_RESERVA_DESCARTADOS

    vigentes = [s for s in servicios if not descartado(s[2], s[3])]
    descartados = len(servicios) - len(vigentes)
    sesiones = {reserva.pk for _fecha, _pk, reserva, _solicitud in vigentes if reserva is not None}

    por_sesion = defaultdict(list)
    maquila = []
    if contexto.base == 'plantas_piloto':
        from apps.plantas_piloto.operacion.models.produccion import OrdenProduccion
        for orden in (OrdenProduccion.objects.filter(unidad=unidad, demostrativa=False)
                      .filter(Q(reserva_id__in=sesiones)
                              | Q(origen='maquila', fecha_inicio__lte=fin, fecha_fin__gte=inicio))
                      .exclude(estado='cancelada').select_related('producto', 'receta', 'reserva__usuario')
                      .order_by('fecha_inicio', 'pk')):
            if orden.reserva_id in sesiones:
                por_sesion[orden.reserva_id].append(orden)
            else:
                maquila.append(orden)

    filas = [(dia, 0, pk, _fila_de_servicio(reserva, solicitud, por_sesion.get(reserva.pk if reserva else None, ())))
             for dia, pk, reserva, solicitud in vigentes]
    filas += [(orden.fecha_inicio, 1, orden.pk, _fila_de_maquila(orden)) for orden in maquila]
    filas.sort(key=lambda fila: fila[:3])
    # Se cuenta el estado que muestra la fila: el de la solicitud operativa o, sin ella, el de la sesión.
    completados = sum((solicitud if solicitud is not None else reserva).estado == 'completada'
                      for _dia, _pk, reserva, solicitud in vigentes)
    pie = f'Total: {plural(len(vigentes), "servicio", "servicios")} · completados: {cifra(completados)}'
    if contexto.base == 'plantas_piloto':
        pie += f' · órdenes de maquila sin solicitud de servicio: {cifra(len(maquila))}'
    if descartados:
        pie += f' · cancelados, rechazados o vencidos, que no se listan: {cifra(descartados)}'
    return Registro('Servicios especializados',
                    ('Solicitud', 'Fecha', 'Solicitante / entidad', 'Tipo de trabajo / modalidad', 'Descripción',
                     'Estado', 'Horas', 'Valor', 'Orden o sesión'),
                    [fila for _dia, _clase, _pk, fila in filas], pesos=(10, 11, 14, 13, 17, 9, 7, 9, 10),
                    total=pie, vacio='No hay servicios especializados registrados en el período.')


def _solicitudes_de_informacion(contexto):
    """Solo el observatorio: lo que se le pidió y lo que respondió."""
    from django.db.models import Q

    from apps.observatorios.operacion.models.observatorios import SolicitudDatos

    periodo = (contexto.inicio, contexto.fin)
    filas = []
    atendidas = 0
    for solicitud in (SolicitudDatos.objects.filter(unidad=contexto.unidad)
                      .filter(Q(creada__date__range=periodo) | Q(atendida__date__range=periodo))
                      .select_related('usuario').order_by('creada', 'pk')):
        atendidas += solicitud.estado == 'atendida'
        filas.append([
            par(fecha(solicitud.creada), f'atendida {fecha(solicitud.atendida)}' if solicitud.atendida else ''),
            par(nombre_de(solicitud.usuario), texto(solicitud.institucion, 90) if solicitud.institucion.strip() else ''),
            solicitud.get_tipo_display(),
            texto(solicitud.descripcion, 220),
            texto(solicitud.finalidad, 140),
            solicitud.get_estado_display(),
            texto(solicitud.respuesta, 220),
        ])
    return Registro('Solicitudes de información atendidas',
                    ('Recibida / atendida', 'Solicitante / institución', 'Qué necesita', 'Detalle', 'Finalidad',
                     'Estado', 'Respuesta'),
                    filas, pesos=(12, 16, 12, 20, 14, 8, 18),
                    total=f'Total: {plural(len(filas), "solicitud", "solicitudes")} · atendidas: {cifra(atendidas)}',
                    vacio='No hay solicitudes de información en el período.')


def transferencia(contexto):
    """Anexo de transferencia de conocimiento, tecnología y servicios especializados (sección 4.11).

    Las transferencias documentadas y los servicios del período; en el observatorio, además, las
    solicitudes de información. En la planta piloto, la maquila se cita por el código de su orden.
    """
    registros = [_transferencias(contexto), _servicios(contexto)]
    if contexto.base == 'observatorios':
        registros.append(_solicitudes_de_informacion(contexto))
    return registros
