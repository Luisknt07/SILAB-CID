"""Respaldo documental de seguridad, inventario y gestión de desechos.

Los registros operativos y su soporte se presentan por separado: una entrada
al laboratorio no demuestra una inspección, y una entrega declarada no
demuestra por sí sola la autorización del gestor ni su recepción del desecho.
Estas lecturas no crean obligaciones, archivos ni evidencias.
"""

from calendar import monthrange
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode

from django.db.models import Count, Q, Sum
from django.urls import reverse
from django.utils import timezone

from apps.documentos.models.expediente import DocumentoExpediente
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.models.respaldo_medicion import corte_efectivo, es_laboratorio, faltantes_desecho
from apps.documentos.models.resultados_gestion import CONDICIONES_REVISION
from apps.documentos.presentation.perfil_unidades import es_unidad_auditable
from apps.gestion_unidades.presentation.reportes_evidencias import (
    reporte_seguridad as _reporte_ingresos,
    reporte_equipamiento as _reporte_equipamiento,
    reporte_prestamos as _reporte_prestamos,
)
from apps.recursos.models.desechos import RegistroDesecho
from apps.recursos.models.consumibles import Consumible, LoteConsumible
from apps.recursos.models.mantenimiento import IncidenciaEquipo, MantenimientoEquipo
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.models.prestamos import PrestamoEquipo
from apps.reservas.models.seguridad import HabilitacionAcceso, RequisitoAcceso


def _nombre(usuario):
    return (usuario.get_full_name() or usuario.get_username()) if usuario else 'Sin asignar'


def _numero(valor):
    """Cantidad decimal legible, sin ceros de almacenamiento ni redondeo binario."""
    numero = valor if isinstance(valor, Decimal) else Decimal(str(valor or 0))
    return format(numero.normalize(), 'f')


def _fecha(valor):
    if not valor:
        return '—'
    if hasattr(valor, 'hour'):
        valor = timezone.localtime(valor) if timezone.is_aware(valor) else valor
    return valor.strftime('%d/%m/%Y')


def _archivo_disponible(archivo):
    """Comprobar existencia no equivale a validar el contenido o su firma."""
    if not archivo or not archivo.name:
        return False
    try:
        return archivo.storage.exists(archivo.name)
    except (OSError, ValueError):
        return False


def _respaldo(archivo):
    if not archivo or not archivo.name:
        return 'Sin archivo adjunto'
    nombre = Path(archivo.name).name
    return nombre if _archivo_disponible(archivo) else f'Archivo no disponible: {nombre}'


def _documentos_seguridad(unidad, desde, hasta):
    corte = min(hasta, timezone.localdate())
    documentos = DocumentoExpediente.objects.filter(
        unidad=unidad,
        exigido__codigo__in=('PROTOCOLO-BIOSEGURIDAD', 'CHEQUEO-SEGURIDAD'),
        anio__lte=corte.year,
    ).select_related('exigido', 'recurso', 'validado_por', 'cargado_por').order_by(
        '-anio', '-mes', '-version', '-pk')
    protocolo = None
    chequeos = []
    for documento in documentos:
        fecha_archivo = documento.cargado_en or documento.generado_en
        if fecha_archivo and timezone.localdate(fecha_archivo) > corte:
            continue
        if documento.exigido.codigo == 'PROTOCOLO-BIOSEGURIDAD':
            # Se hereda el último protocolo disponible, nunca un pendiente
            # virtual del año nuevo que oculte el documento del año anterior.
            if protocolo is None or (not protocolo.recurso_id and documento.recurso_id):
                protocolo = documento
        elif documento.mes:
            inicio = date(documento.anio, documento.mes, 1)
            fin = date(documento.anio, documento.mes, monthrange(documento.anio, documento.mes)[1])
            if inicio <= corte and fin >= desde:
                chequeos.append(documento)
        elif fecha_archivo and desde <= timezone.localdate(fecha_archivo) <= corte:
            chequeos.append(documento)
    from apps.documentos.presentation.cumplimiento import preparar_vigencias_exportacion
    preparar_vigencias_exportacion([protocolo] if protocolo else [])
    return protocolo, chequeos


def _documento_respaldado(documento, unidad):
    return bool(documento and documento.recurso_id
                and documento.recurso.unidad_id == unidad.pk
                and documento.recurso.activo
                and _archivo_disponible(documento.recurso.archivo))


def _inspecciones(unidad, desde, hasta):
    from apps.documentos.presentation.medicion_metas import inspecciones_documentadas
    datos = inspecciones_documentadas(unidad, desde, min(hasta, timezone.localdate()))
    return [fila for fila in datos['filas'] if fila['estado'] != 'anulado']


def reporte_seguridad(unit, start_date, end_date, state='', search=''):
    """Ingresos del período con cobertura documental y de inducciones explícita."""
    hasta_ingresos = corte_efectivo(unit, end_date)
    headers, rows, cards, choices = _reporte_ingresos(unit, start_date, hasta_ingresos, state, search)
    corte = min(end_date, timezone.localdate())
    protocolo, chequeos = _documentos_seguridad(unit, start_date, end_date)
    habilitaciones = HabilitacionAcceso.objects.filter(requisito__unidad=unit, activa=True, fecha__lte=corte)
    vigentes = habilitaciones.filter(Q(vence__isnull=True) | Q(vence__gte=corte)).count()
    cards = [(titulo, vigentes, f'al {_fecha(corte)}') if titulo == 'Habilitaciones vigentes'
             else (titulo, valor, *extra) for titulo, valor, *extra in cards]
    inducciones = HabilitacionAcceso.objects.filter(
        requisito__unidad=unit, requisito__tipo='induccion',
        fecha__range=(start_date, corte), activa=True,
    )
    inspecciones = _inspecciones(unit, start_date, end_date)
    from apps.documentos.presentation.cumplimiento import vigencia_exportada
    cards.extend([
        ('Protocolo con archivo', 'Sí' if _documento_respaldado(protocolo, unit) else 'Pendiente',
         (vigencia_exportada(protocolo) or protocolo.get_estado_display()) if protocolo else 'sin documento registrado'),
        ('Inducciones del período', inducciones.count(), 'habilitaciones activas otorgadas'),
        ('Inspecciones con archivo', sum(_documento_respaldado(d, unit) for d in chequeos),
         'listas de chequeo históricas adjuntas'),
        ('Inspecciones documentadas', len(inspecciones), 'controles y hallazgos del período'),
        ('Inspecciones verificadas reales', sum(f['acredita'] for f in inspecciones),
         'con respaldo vigente; excluye demostraciones'),
        ('Inspecciones de demostración', sum(f['demostracion'] for f in inspecciones),
         'no acreditan el cierre institucional'),
    ])
    if es_laboratorio(unit):
        from apps.documentos.presentation.medicion_metas import cobertura_mensual_inspecciones
        mensual = cobertura_mensual_inspecciones(unit, start_date, end_date)
        cards.extend([
            ('Meses con revisión verificada', f'{mensual["cubiertos"]}/{mensual["exigidos"]}',
             f'cobertura documental hasta {_fecha(date.fromisoformat(mensual["corte"]))}'),
            ('Meses vencidos sin revisión', mensual['vencidos_sin_revision'],
             f'{mensual["pendientes_en_plazo"]} mes en curso pendiente dentro de plazo'),
        ])
    return headers, rows, cards, choices


def reporte_equipamiento(unit, start_date, end_date, state='', search=''):
    """Disponibilidad observada hasta hoy, sin extender estados a días futuros."""
    corte = corte_efectivo(unit, end_date)
    if es_unidad_auditable(unit) and corte < start_date:
        from apps.recursos.models.unidades import UnidadEquipo
        return (['Código', 'Equipo', 'Ubicación', 'Estado actual', 'Disponible en el período',
                 'Días fuera de servicio', 'Mantenimientos (completados)', 'Incidencias', 'Próximo mantenimiento'],
                [], [('Período aún no iniciado', 'Sin medición', f'fecha de corte {_fecha(corte)}')],
                UnidadEquipo._meta.get_field('estado_unidad').choices)
    headers, rows, cards, choices = _reporte_equipamiento(unit, start_date, corte, state, search)
    if es_unidad_auditable(unit):
        cards = [(titulo, valor, f'observada hasta {_fecha(corte)}') if titulo == 'Disponibilidad media'
                 else (titulo, valor, *extra) for titulo, valor, *extra in cards]
        funcionalidad = _funcionalidad(unit, start_date, end_date, state, search)
        cards.extend([
            ('Equipos con prueba funcional del período',
             f'{funcionalidad["comprobados_en_periodo"]}/{funcionalidad["universo_equipos"]}',
             'pruebas reales verificadas; el estado operativo no acredita una comprobación'),
            ('Sin prueba funcional del período', funcionalidad['sin_comprobacion_periodo'],
             f'hasta {_fecha(corte)}'),
            ('Resultado de las pruebas funcionales',
             f'{funcionalidad["operativos"]} operativos · {funcionalidad["observados"]} observados · '
             f'{funcionalidad["no_operativos"]} no operativos',
             'según el procedimiento y la fecha documentados; no autoriza por sí solo la operación'),
        ])
    return headers, rows, cards, choices


def _funcionalidad(unidad, desde, hasta, estado='', buscar=''):
    from apps.documentos.presentation.funcionalidad_laboratorios import funcionalidad_documentada
    datos = funcionalidad_documentada(unidad, desde, hasta)
    equipos = (UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad))
               .exclude(activa=False, fecha_baja__isnull=True).distinct())
    if estado in dict(UnidadEquipo.ESTADO_UNIDAD_CHOICES):
        equipos = equipos.filter(estado_unidad=estado)
    if buscar:
        equipos = equipos.filter(Q(codigo_unidad__icontains=buscar) | Q(equipo__nombre__icontains=buscar)
                                  | Q(ubicacion_especifica__icontains=buscar))
    ids = set(equipos.values_list('pk', flat=True))
    datos['ultimas'] = [f for f in datos['ultimas'] if f['equipo_id'] in ids]
    datos['filas'] = [f for f in datos['filas'] if f['equipo_id'] in ids]
    datos.update(universo_equipos=len(datos['ultimas']),
        comprobados_en_periodo=sum(f['vigente_en_periodo'] for f in datos['ultimas']),
        sin_comprobacion_periodo=sum(f['pendiente'] for f in datos['ultimas']),
        operativos=sum(f['vigente_en_periodo'] and f['apto'] for f in datos['ultimas']),
        observados=sum(f['vigente_en_periodo'] and f['resultado_funcional'] == 'observado' for f in datos['ultimas']),
        no_operativos=sum(f['vigente_en_periodo'] and f['no_apto'] for f in datos['ultimas']))
    return datos


def reporte_prestamos(unit, start_date, end_date, state='', search=''):
    """Las salidas históricas incompletas siguen visibles con sus faltantes."""
    headers, rows, cards, choices = _reporte_prestamos(unit, start_date, end_date, state, search)
    if not es_laboratorio(unit):
        return headers, rows, cards, choices
    from apps.documentos.models.respaldo_medicion import validar_respaldo
    from django.core.exceptions import ValidationError
    prestamos = {p.codigo: p for p in PrestamoEquipo.objects.filter(
        unidad=unit, codigo__in=[r[0] for r in rows]).select_related('entregado_por', 'recibido_por')}
    headers = list(headers) + ['Entregado por', 'Recibido por', 'Pendientes de respaldo']
    for fila in rows:
        prestamo = prestamos[fila[0]]
        pendientes = []
        if prestamo.estado != 'solicitado' and prestamo.estado != 'cancelado':
            if not prestamo.entregado_por_id:
                pendientes.append('responsable de entrega')
            if prestamo.tipo == 'externo':
                if not prestamo.institucion.strip():
                    pendientes.append('institución receptora')
                if not prestamo.autorizado_por.strip():
                    pendientes.append('autorización de salida')
                try:
                    if not prestamo.acta:
                        raise ValidationError('Sin acta.')
                    validar_respaldo(prestamo.acta)
                except ValidationError:
                    pendientes.append('acta legible y disponible')
            if prestamo.estado == 'devuelto':
                if not prestamo.recibido_por_id:
                    pendientes.append('responsable de recepción')
                if not prestamo.condicion_retorno:
                    pendientes.append('condición de retorno')
                if not prestamo.fecha_retorno_real:
                    pendientes.append('fecha real de devolución')
        situacion = '; '.join(pendientes) or ('Solicitud en preparación' if prestamo.estado == 'solicitado' else
                                             'Datos de custodia registrados')
        fila.extend([_nombre(prestamo.entregado_por), _nombre(prestamo.recibido_por), situacion])
    return headers, rows, cards, choices


def _desechos(unidad, desde, hasta, estado='', buscar=''):
    # Incluye entregas del período aunque se hayan generado antes: de otro
    # modo desaparecía del informe la salida de existencias acumuladas.
    queryset = RegistroDesecho.objects.filter(unidad=unidad).filter(
        Q(fecha_generacion__range=(desde, hasta)) | Q(fecha_entrega__range=(desde, hasta))
        | Q(fecha_generacion__lt=desde, etapa='almacenado')
        | Q(fecha_generacion__lt=desde, etapa='entregado', fecha_entrega__gt=hasta),
    ).select_related('unidad', 'responsable', 'registrado_por').order_by('fecha_generacion', 'pk')
    if estado in dict(RegistroDesecho.ETAPAS):
        queryset = queryset.filter(etapa=estado)
    if buscar:
        queryset = queryset.filter(
            Q(nombre__icontains=buscar) | Q(clave_listado__icontains=buscar)
            | Q(origen__icontains=buscar) | Q(gestor_autorizado__icontains=buscar)
            | Q(manifiesto__icontains=buscar) | Q(licencia_gestor__icontains=buscar)
            | Q(almacenamiento__icontains=buscar)
        )
    return queryset


def pendientes_desecho(item, al_corte=None):
    """Faltantes de trazabilidad, sin emitir una conclusión legal automática."""
    if es_laboratorio(item.unidad):
        return faltantes_desecho(item, validar_archivo=True, al_corte=al_corte)
    faltantes = []
    for campo, etiqueta in (('clave_listado', 'clave del listado aplicable'), ('origen', 'origen'),
                            ('envase', 'envase'), ('almacenamiento', 'almacenamiento')):
        if not (getattr(item, campo) or '').strip():
            faltantes.append(etiqueta)
    if not item.etiquetado:
        faltantes.append('etiquetado sin confirmar')
    if not item.responsable_id:
        faltantes.append('responsable')
    if item.etapa == 'entregado':
        for campo, etiqueta in (('fecha_entrega', 'fecha de entrega'),
                                ('gestor_autorizado', 'gestor'), ('licencia_gestor', 'licencia del gestor'),
                                ('manifiesto', 'manifiesto')):
            if not getattr(item, campo):
                faltantes.append(etiqueta)
        if not _archivo_disponible(item.documento):
            faltantes.append('archivo del manifiesto o acta')
    elif item.etapa == 'tratado':
        if not item.observaciones.strip():
            faltantes.append('procedimiento y resultado del tratamiento')
        if not _archivo_disponible(item.documento):
            faltantes.append('acta del tratamiento')
    return faltantes


def reporte_desechos(unit, start_date, end_date, state='', search=''):
    """Resumen compacto; el detalle de respaldo se conserva en tablas adicionales."""
    end_date = corte_efectivo(unit, end_date)
    queryset = _desechos(unit, start_date, end_date, state, search)
    headers = ['Generado', 'Desecho / clave', 'Clase / estado físico', 'Origen', 'Cantidad',
               'Envase / almacenamiento', 'Etapa', 'Entrega / manifiesto', 'Responsable', 'Pendientes de respaldo']
    rows = []
    for item in queryset[:501]:
        entrega_en_periodo = item.fecha_entrega and start_date <= item.fecha_entrega <= end_date
        # Si se consulta un corte histórico anterior a la entrega, el registro
        # sigue figurando almacenado y no se adelanta la salida posterior.
        entrega_futura = item.fecha_entrega and item.fecha_entrega > end_date
        etapa = 'Almacenado al cierre consultado' if entrega_futura and item.etapa == 'entregado' else item.get_etapa_display()
        rows.append([
            _fecha(item.fecha_generacion), f'{item.nombre} · {item.clave_listado or "Sin clave"}',
            f'{item.get_clase_display()} · {item.get_estado_fisico_display()}', item.origen or 'Sin registrar',
            f'{_numero(item.cantidad)} {item.get_unidad_medida_display()}',
            f'{item.envase or "Sin envase"} · {item.almacenamiento or "Sin ubicación"}', etapa,
            f'{_fecha(item.fecha_entrega)} · {item.manifiesto or "Sin manifiesto"}'
            if entrega_en_periodo else 'Posterior al corte' if entrega_futura else '—',
            _nombre(item.responsable), '; '.join(pendientes_desecho(item, end_date)) or 'Datos y respaldo registrados',
        ])
    totales = queryset.aggregate(
        total=Count('pk'),
        generados=Count('pk', filter=Q(fecha_generacion__range=(start_date, end_date))),
        entregados=Count('pk', filter=Q(etapa='entregado', fecha_entrega__range=(start_date, end_date))),
        almacenados=Count('pk', filter=Q(etapa='almacenado')
                         | Q(etapa='entregado', fecha_entrega__gt=end_date)),
        sin_responsable=Count('pk', filter=Q(responsable__isnull=True)),
    )
    cards = [('Registros', totales['total'], f'{totales["generados"]} generados en el período'),
             ('Entregados a gestor', totales['entregados'], 'con fecha de entrega en el período'),
             ('Almacenados sin entregar', totales['almacenados']),
             ('Sin responsable', totales['sin_responsable'])]
    # Cada unidad conserva su propio total: nunca sumar litros con kg.
    for clave, etiqueta in RegistroDesecho.UNIDADES:
        total = queryset.filter(fecha_generacion__range=(start_date, end_date), unidad_medida=clave).aggregate(
            total=Sum('cantidad'))['total'] or 0
        nombre = {'kg': 'Kilogramos registrados', 'l': 'Litros registrados', 'unidad': 'Unidades registradas'}[clave]
        cards.append((nombre, _numero(total), 'generados en el período'))
    return headers, rows, cards, RegistroDesecho.ETAPAS


def _tabla(titulo, headers, rows, vacio):
    if len(rows) >= 200:
        titulo += ' · hasta 200 registros; ajusta la selección para consultar el resto'
    return {'titulo': titulo, 'headers': headers, 'rows': rows, 'vacio': vacio}


def _tablas_seguridad(unidad, desde, hasta):
    from apps.documentos.presentation.cumplimiento import vigencia_exportada

    corte = min(hasta, timezone.localdate())
    protocolo, chequeos = _documentos_seguridad(unidad, desde, hasta)
    documentos = []
    for documento in ([protocolo] if protocolo else []) + chequeos:
        respaldo = _documento_respaldado(documento, unidad)
        recurso = documento.recurso
        vigencia = vigencia_exportada(documento)
        aprobacion = getattr(documento, 'aprobacion_permanente', {}) or {}
        observacion = (aprobacion.get('comentario') or aprobacion.get('motivo') or documento.observacion)
        if vigencia:
            observacion = 'Aprobación técnica única.' + (f' {observacion}' if observacion else '')
        else:
            observacion = documento.observacion or ('Pendiente de validación'
                if respaldo and documento.estado != 'validado' else 'Sin respaldo disponible' if not respaldo else '—')
        documentos.append([
            documento.exigido.nombre, documento.etiqueta_corte, vigencia or documento.get_estado_display(),
            _respaldo(recurso.archivo) if recurso and recurso.unidad_id == unidad.pk else 'Sin archivo de esta unidad',
            f'v{documento.version}', 'Sí' if documento.firma_verificada else 'Sin verificar',
            _nombre(documento.validado_por or documento.cargado_por),
            observacion,
        ])
    if protocolo is None:
        documentos.insert(0, ['Protocolo de seguridad y condiciones de operación', 'Documento permanente',
                             'Pendiente de aprobación', 'Sin archivo adjunto', '—', 'Sin verificar', 'Sin asignar',
                             'Cargar y validar el protocolo de la unidad; requiere aprobación técnica única.'])
    requisitos = RequisitoAcceso.objects.filter(unidad=unidad, activo=True).order_by('orden', 'nombre')
    requisitos_rows = [[r.codigo, r.nombre, r.get_tipo_display(), r.categorias_display,
                        'Sí' if r.obligatorio else 'No', r.get_momento_display(),
                        f'{r.vigencia_dias} días' if r.vigencia_dias else 'Sin vencimiento',
                        r.descripcion or '—'] for r in requisitos[:200]]
    habilitaciones = HabilitacionAcceso.objects.filter(
        requisito__unidad=unidad, fecha__range=(desde, corte),
    ).select_related('requisito', 'usuario', 'otorgada_por', 'reserva').order_by('fecha', 'pk')
    habilitaciones_rows = [[_fecha(h.fecha), _nombre(h.usuario), h.requisito.nombre,
                            h.get_origen_display(), h.documento or
                            (h.reserva.codigo_reserva if h.reserva_id else 'Sin referencia'),
                            _fecha(h.vence), 'Vigente al corte' if h.vigente_en(corte) else 'Vencida o inactiva',
                            _nombre(h.otorgada_por), h.observaciones or '—'] for h in habilitaciones[:200]]
    incidencias = IncidenciaEquipo.objects.filter(
        Q(unidad=unidad) | Q(unidad__isnull=True, equipo__laboratorio=unidad)
        | Q(unidad__isnull=True, equipo__laboratorios=unidad),
        tipo='seguridad', fecha_reporte__date__range=(desde, corte),
    ).distinct().select_related('equipo', 'reportada_por', 'asignada_a').order_by('fecha_reporte', 'pk')
    incidencias_rows = [[_fecha(i.fecha_reporte), i.equipo.codigo_unidad, i.titulo,
                         i.get_prioridad_display(), i.get_estado_display(),
                         'Sí' if i.detiene_operacion else 'No', _nombre(i.asignada_a),
                         i.solucion or 'Sin solución registrada', _respaldo(i.evidencia)] for i in incidencias[:200]]
    inspecciones_rows = []
    for fila in _inspecciones(unidad, desde, hasta)[:200]:
        detalle = fila['detalle']
        condiciones = detalle.get('condiciones_revisadas', [])
        revisadas = ', '.join(dict(CONDICIONES_REVISION).get(c, str(c).replace('_', ' '))
                              for c in condiciones) if isinstance(condiciones, list) else 'Sin alcance registrado'
        estado_condiciones = {'seguro': 'Sin restricciones declaradas', 'observado': 'Con observaciones',
                              'no_operar': 'No operar según la inspección'}.get(
                                  detalle.get('estado_condiciones'), 'Sin conclusión registrada')
        estado_accion = {'no_requiere': 'No requiere acción', 'pendiente': 'Pendiente de resolver',
                        'resuelta': 'Resuelta según el registro'}.get(detalle.get('estado_accion'), 'Sin estado registrado')
        estado_respaldo = ('Verificada con respaldo' if fila['acredita'] else
                           'Demostración; no acredita' if fila['demostracion'] else 'Pendiente de completar o verificar')
        inspecciones_rows.append([
            f"{fila['codigo']} · {_fecha(fila['fecha'])}", detalle.get('area') or 'Sin área',
            revisadas or 'Sin alcance registrado',
            'Sin hallazgos declarados' if detalle.get('sin_hallazgos') else detalle.get('hallazgos') or 'Sin hallazgos documentados',
            estado_condiciones,
            (detalle.get('accion_correctiva') or estado_accion) +
            (f" · Plazo: {detalle['plazo_accion']}" if detalle.get('plazo_accion') else ''),
            fila['responsable'], f"{fila['estado_display']} · {estado_respaldo}",
        ])
    tablas = [
        _tabla('Protocolo y listas de chequeo de condiciones de operación',
               ['Documento', 'Cobertura', 'Estado', 'Respaldo', 'Versión', 'Firma verificada',
                'Responsable del registro', 'Observaciones'], documentos,
               'Sin protocolos ni listas de chequeo registrados.'),
        _tabla('Inspecciones de bioseguridad y condiciones de operación documentadas',
               ['Registro / fecha', 'Área inspeccionada', 'Condiciones revisadas', 'Hallazgos',
                'Condición declarada', 'Acción y plazo', 'Responsable', 'Estado del respaldo'], inspecciones_rows,
               'Sin inspecciones documentadas. Registra la revisión, sus hallazgos y el respaldo en Evidencias de la unidad.'),
        _tabla('Requisitos de acceso y bioseguridad configurados',
               ['Código', 'Requisito', 'Tipo', 'Personas a las que aplica', 'Obligatorio',
                'Verificación', 'Vigencia', 'Indicaciones'], requisitos_rows,
               'No se han configurado requisitos. La ausencia de requisitos no acredita seguridad.'),
        _tabla('Inducciones y habilitaciones otorgadas en el período',
               ['Fecha', 'Persona', 'Requisito', 'Origen', 'Certificado / sesión', 'Vence',
                'Estado al corte', 'Otorgada por', 'Observaciones'], habilitaciones_rows,
               'Sin inducciones ni habilitaciones registradas en el período.'),
        _tabla('Incidencias de seguridad de equipos reportadas en el período',
               ['Fecha', 'Equipo', 'Hallazgo', 'Prioridad', 'Estado', 'Detuvo operación',
                'Asignada a', 'Solución', 'Evidencia'], incidencias_rows,
               'Sin incidencias reportadas; esto no sustituye una inspección de condiciones.'),
    ]
    if es_laboratorio(unidad):
        from apps.documentos.presentation.medicion_metas import cobertura_mensual_inspecciones
        mensual = cobertura_mensual_inspecciones(unidad, desde, hasta)
        tablas.insert(1, _tabla('Cobertura mensual de inspecciones documentadas',
            ['Mes', 'Tramo aplicable', 'Revisiones registradas', 'Verificadas reales', 'Demostraciones',
             'Resultado documental', 'Referencias verificadas', 'Áreas revisadas'],
            [[m['mes'], f"{m['desde']} – {m['hasta']}", m['revisiones'], m['verificadas_reales'], m['demostracion'],
              m['estado'], ', '.join(m['codigos']) or 'Sin respaldo verificado', ', '.join(m['areas']) or 'Sin área verificada']
             for m in mensual['meses']],
            'El período aún no ha empezado; no se atribuye cobertura a meses futuros.'))
    return tablas


def _tablas_desechos(unidad, desde, hasta, estado, buscar):
    hasta = corte_efectivo(unidad, hasta)
    rows = []
    for item in _desechos(unidad, desde, hasta, estado, buscar)[:200]:
        rows.append([
            f'{_fecha(item.fecha_generacion)} · {item.nombre}',
            'Confirmado' if item.etiquetado else 'Sin confirmar',
            item.gestor_autorizado or 'Sin registrar', item.licencia_gestor or 'Sin registrar',
            item.manifiesto or 'Sin registrar', _respaldo(item.documento),
            _nombre(item.registrado_por), item.observaciones or '—',
        ])
    return [_tabla('Respaldo de almacenamiento, tratamiento y entrega de desechos',
                   ['Registro', 'Etiquetado', 'Gestor autorizado declarado', 'Licencia / registro',
                    'Manifiesto', 'Archivo de respaldo', 'Registrado por', 'Observaciones'], rows,
                   'Sin generaciones o entregas de desechos registradas en el período.')]


def _tablas_inventario(unidad, desde, hasta, buscar, estado=''):
    hasta = corte_efectivo(unidad, hasta)
    # El inventario lista lo que existe y las bajas con su historia; las referencias no son inventario.
    equipos = (UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad))
               .exclude(activa=False, fecha_baja__isnull=True).distinct())
    if estado in dict(UnidadEquipo.ESTADO_UNIDAD_CHOICES):
        equipos = equipos.filter(estado_unidad=estado)
    if buscar:
        equipos = equipos.filter(Q(codigo_unidad__icontains=buscar) | Q(codigo_bien__icontains=buscar)
                                  | Q(equipo__nombre__icontains=buscar))
    equipos = equipos.select_related('equipo', 'existencia_verificada_por').order_by('codigo_unidad')
    rows = []
    for equipo in equipos[:200]:
        pendientes = []
        for valor, etiqueta in ((equipo.codigo_bien, 'código del bien'),
                                 (equipo.custodio, 'custodio'), (equipo.ubicacion_especifica, 'ubicación'),
                                 (equipo.numero_serie, 'serie')):
            if not valor:
                pendientes.append(etiqueta)
        if not equipo.existencia_verificada:
            pendientes.append('verificación física')
        ficha = _respaldo(equipo.equipo.ficha_tecnica) if equipo.equipo.ficha_tecnica else (
            'Especificaciones estructuradas' if equipo.equipo.especificaciones else 'Sin ficha ni especificaciones')
        con_texto = es_laboratorio(unidad) and bool(equipo.equipo.caracteristicas_publicas.strip())
        if con_texto and not equipo.equipo.ficha_tecnica and not equipo.equipo.especificaciones:
            ficha = 'Características técnicas en texto; sin ficha formal adjunta'
        if not equipo.equipo.ficha_tecnica and not equipo.equipo.especificaciones and not con_texto:
            pendientes.append('ficha técnica o especificaciones')
        rows.append([equipo.codigo_unidad, equipo.equipo.nombre, equipo.codigo_bien or 'Sin registrar',
                     equipo.numero_serie or 'Sin registrar', equipo.custodio or 'Sin asignar',
                     equipo.ubicacion_especifica or equipo.ubicacion_bodega or 'Sin registrar',
                     f'Verificada {_fecha(equipo.existencia_verificada_en)}' if equipo.existencia_verificada
                     else 'Sin verificar', _nombre(equipo.existencia_verificada_por),
                     ficha, '; '.join(pendientes) or 'Datos de identificación registrados'])
    actas = EvidenciaGestionUnidad.objects.filter(
        unidad=unidad, tipo='INVENTARIO', fecha__range=(desde, hasta),
    ).select_related('responsable', 'validado_por', 'recurso').order_by('fecha', 'pk')
    actas = list(actas[:200])
    from apps.documentos.presentation.medicion_metas import evidencias_verificadas
    actas_verificadas = {a.pk for a in evidencias_verificadas(unidad, actas, desde, hasta)}
    actas_rows = [[a.codigo, _fecha(a.fecha), a.titulo,
                   'Verificación pendiente de alcance o respaldo' if a.estado == 'validado' and a.pk not in actas_verificadas else a.get_estado_display(),
                   ', '.join(a.alcance) if isinstance(a.alcance, list) else 'Sin alcance verificable',
                   _nombre(a.responsable), _respaldo(a.recurso.archivo) if a.recurso_id else a.enlace or 'Sin respaldo',
                   'Demostración; no acredita el cierre' if a.demostracion else 'Registro operativo'] for a in actas]
    tablas = [
        _tabla('Identificación y verificación física del equipamiento',
               ['Código de unidad', 'Equipo', 'Código institucional del bien', 'Serie', 'Custodio',
                'Ubicación', 'Existencia física', 'Verificada por',
                'Documentación técnica' if es_laboratorio(unidad) else 'Ficha técnica', 'Pendientes'], rows,
               'Sin equipos asignados a esta unidad.'),
        _tabla('Actas de revisión de inventario del período',
               ['Código', 'Fecha', 'Acta', 'Estado', 'Alcance', 'Responsable', 'Respaldo', 'Carácter del registro'],
               actas_rows, 'Sin actas de revisión de inventario registradas en el período.'),
    ]
    if es_laboratorio(unidad):
        tablas.extend(_tablas_insumos(unidad, buscar))
    return tablas


def _tablas_insumos(unidad, buscar):
    insumos = Consumible.objects.filter(unidad=unidad, activo=True)
    lotes = LoteConsumible.objects.filter(consumible__unidad=unidad).select_related(
        'consumible', 'equipo_en_uso').order_by('consumible__nombre', 'fecha_vencimiento', 'codigo')
    if buscar:
        insumos = insumos.filter(Q(codigo__icontains=buscar) | Q(nombre__icontains=buscar))
        lotes = lotes.filter(Q(consumible__codigo__icontains=buscar) | Q(consumible__nombre__icontains=buscar)
                            | Q(codigo__icontains=buscar))
    insumos = insumos.annotate(saldo_lotes=Sum('lotes_inventario__cantidad_actual')).order_by('nombre')
    rows = []
    for insumo in insumos[:200]:
        pendientes = []
        if not insumo.ubicacion:
            pendientes.append('ubicación')
        if not insumo.unidad_medida:
            pendientes.append('unidad de medida')
        if insumo.saldo_lotes is None:
            conciliacion = 'Sin lotes físicos registrados'
        elif insumo.saldo_lotes != insumo.stock_total:
            conciliacion = f'Diferencia: {_numero(insumo.stock_total - insumo.saldo_lotes)} {insumo.unidad_medida or ""}'
        else:
            conciliacion = 'Saldo y lotes coinciden'
        rows.append([insumo.codigo, insumo.nombre, insumo.get_clasificacion_display(),
                     f'{_numero(insumo.stock_total)} {insumo.unidad_medida or "Sin unidad"}', insumo.ubicacion or 'Sin registrar',
                     f'{_numero(insumo.minimo)} {insumo.unidad_medida or ""}', conciliacion,
                     _respaldo(insumo.ficha_tecnica), '; '.join(pendientes) or 'Datos básicos registrados'])
    lotes_rows = []
    hoy = timezone.localdate()
    for lote in lotes[:200]:
        caducidad = ('Vencido' if lote.fecha_vencimiento < hoy else 'Vigente') if lote.fecha_vencimiento else 'Sin vencimiento registrado'
        lotes_rows.append([lote.consumible.codigo, lote.codigo,
                           f'{_numero(lote.cantidad_actual)} {lote.consumible.unidad_medida or "Sin unidad"}',
                           lote.get_estado_display(), lote.ubicacion_completa, _fecha(lote.fecha_ingreso),
                           _fecha(lote.fecha_vencimiento), caducidad, lote.documento_recepcion or 'Sin respaldo de recepción'])
    return [
        _tabla('Existencias actuales de reactivos e insumos',
               ['Código', 'Artículo', 'Clasificación', 'Saldo actual', 'Ubicación', 'Mínimo de reposición',
                'Conciliación con lotes físicos', 'Ficha técnica adjunta', 'Pendientes'], rows,
               'Sin reactivos ni insumos activos registrados.'),
        _tabla('Lotes físicos: ubicación, vencimiento y respaldo de recepción',
               ['Artículo', 'Lote', 'Saldo actual', 'Estado', 'Ubicación', 'Ingreso', 'Vencimiento',
                'Condición actual de vencimiento', 'Recepción'], lotes_rows,
               'Sin lotes físicos registrados. El saldo general no acredita su localización o vencimiento.'),
    ]


def _tablas_mantenimiento(unidad, desde, hasta, estado, buscar):
    corte = corte_efectivo(unidad, hasta)
    equipos = UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad)).values('pk')
    alcance = Q(unidad=unidad) | Q(unidad__isnull=True, equipo_id__in=equipos)
    ordenes = MantenimientoEquipo.objects.filter(
        alcance, fecha_programada__date__range=(desde, hasta),
    ).select_related('equipo__equipo', 'responsable', 'plan').distinct().order_by('fecha_programada', 'pk')
    if buscar:
        ordenes = ordenes.filter(Q(equipo__codigo_unidad__icontains=buscar)
                                | Q(equipo__equipo__nombre__icontains=buscar)
                                | Q(plan__nombre__icontains=buscar))
    if estado:
        from apps.recursos.presentation.mantenimiento_panel import filas_de_equipos, SEMAFOROS
        if estado in SEMAFOROS:
            ids = [fila['equipo'].pk for fila in filas_de_equipos(unidad) if fila['semaforo'] == estado]
            ordenes = ordenes.filter(equipo_id__in=ids)
    rows = []
    for orden in ordenes[:200]:
        pendientes = []
        if not orden.responsable_id:
            pendientes.append('responsable')
        if orden.estado == 'completado':
            if not orden.resultado.strip():
                pendientes.append('resultado')
            if not orden.fecha_inicio or not orden.fecha_fin:
                pendientes.append('fechas reales')
            if not _archivo_disponible(orden.informe):
                pendientes.append('informe adjunto')
        estado_lectura = orden.get_estado_display()
        if (es_unidad_auditable(unidad) and orden.fecha_fin and
                timezone.localtime(orden.fecha_fin).date() > corte and orden.estado == 'completado'):
            estado_lectura = 'Ejecución posterior al corte; no acredita aún'
        rows.append([
            orden.codigo, orden.equipo.codigo_unidad, orden.get_tipo_display(),
            _fecha(orden.fecha_programada), f'{_fecha(orden.fecha_inicio)} – {_fecha(orden.fecha_fin)}',
            estado_lectura, _nombre(orden.responsable),
            orden.resultado or 'Sin resultado registrado', _respaldo(orden.informe),
            '; '.join(pendientes) or 'Datos y respaldo registrados',
        ])
    tablas = [_tabla('Órdenes de mantenimiento y respaldo de su ejecución',
                   ['Orden', 'Equipo', 'Tipo', 'Programada', 'Inicio – fin reales', 'Estado',
                    'Responsable', 'Resultado', 'Informe adjunto', 'Pendientes'], rows,
                   'Sin órdenes programadas en el período consultado.')]
    if es_unidad_auditable(unidad):
        from apps.documentos.presentation.medicion_metas import medir_mantenimiento_integral
        medida_integral = medir_mantenimiento_integral(unidad, desde, hasta)
        medida = medida_integral['equipos']
        sin_acreditar = {f['codigo']: f['faltantes'] for f in medida['ordenes_no_acreditables']}
        for fila in rows:
            if fila[0] in sin_acreditar:
                otros = [] if fila[9] == 'Datos y respaldo registrados' else [fila[9]]
                fila[9] = '; '.join(otros + sin_acreditar[fila[0]])
        pendiente_equipos = (medida['motivo'] or ', '.join(medida['completadas_sin_respaldo']) or
            ('Sin equipos críticos: revisión del inventario respaldada' if medida['no_aplica_verificado'] else
             'Sin faltantes de registro'))
        tablas.insert(0, _tabla('Alcance del programa anual de equipos críticos de la unidad',
            ['Año', 'Corte efectivo', 'Equipos críticos', 'Sin plan', 'Sin responsable del plan',
             'Sin programación anual', 'Órdenes exigibles', 'Ejecuciones acreditables', 'Pendientes de respaldo / universo'],
            [[desde.year, _fecha(corte), medida['equipos_criticos'], medida['equipos_sin_plan'],
              medida['equipos_sin_responsable'], medida['equipos_sin_programacion'], medida['denominador'],
              medida['numerador'], pendiente_equipos]],
            'Sin universo crítico declarado.'))
        tablas.extend(_tablas_infraestructura(unidad, desde, hasta))
        infra = medida_integral['infraestructura']
        tablas.append(_tabla('Medición del programa anual crítico al corte efectivo',
            ['Alcance', 'Programadas exigibles', 'Ejecuciones respaldadas', 'Programación futura', 'Situación'],
            [['Equipos críticos', medida['denominador'], medida['numerador'], medida['programadas_futuras'],
              'Sin equipos críticos: revisión respaldada' if medida['no_aplica_verificado'] else
              medida['motivo'] or 'Universo y programación identificados'],
             ['Infraestructura crítica', infra['denominador'], infra['numerador'], infra['programadas_futuras'],
              'Sin intervenciones críticas: alcance respaldado' if infra['no_aplica_verificado'] else
              infra['motivo'] or 'Universo y programación identificados'],
             ['Total de la meta institucional (80 %)', medida_integral['denominador'],
              medida_integral['numerador'], medida_integral['programadas_futuras'],
              medida_integral['motivo'] or 'Ejecuciones con resultado, responsable y respaldo; no incluye DEMO']],
            'Sin medición crítica disponible.'))
    return tablas


def _tablas_infraestructura(unidad, desde, hasta):
    """Planes, fechas y resultados, separados de la revisión de bioseguridad."""
    from apps.documentos.presentation.infraestructura_laboratorios import infraestructura_documentada
    anual_inicio, anual_fin = date(desde.year, 1, 1), date(desde.year, 12, 31)
    datos = infraestructura_documentada(unidad, anual_inicio, anual_fin)
    pendientes = {e['pk'] for e in datos['espacios_sin_cobertura']}
    espacios_rows = [[e['codigo'], e['nombre'],
        'Sin plan verificado para este espacio' if e['pk'] in pendientes else
        'Cubierto por declaración anual de no aplicación' if datos['no_aplica'] else
        'Con plan verificado o alcance global documentado'] for e in datos['espacios_del_laboratorio']]
    planes = [p for p in datos['planes'] if p['estado'] != 'anulado']
    ejecuciones = [p for p in datos['ejecuciones'] if p['estado'] != 'anulado']
    planes_rows = [[p['codigo'], p['titulo'], _fecha(p['fecha']),
        'No aplica: ' + p['justificacion_alcance'] if p['alcance_infraestructura'] == 'no_aplica' else
        f'{p["ubicacion"]} · {p["intervencion"]}', p['criticidad_display'], p['responsable'],
        p['fecha_programada'] or 'No aplica',
        f'Cada {p["frecuencia_dias"]} días' if p['frecuencia_dias'] else 'Intervención única' if
        p['alcance_infraestructura'] == 'aplica' else 'Declaración anual',
        p['estado_display']] for p in planes[:200]]
    ocurrencias = sorted(datos['ocurrencias'] + datos['futuras'], key=lambda f: (f['fecha_programada'], f['plan_codigo']))
    ocurrencias_rows = [[f['plan_codigo'], f['ubicacion'], f['intervencion'],
        'Crítica' if f['criticidad'] == 'critica' else f['criticidad'].capitalize(),
        f['fecha_programada'], f['responsable'], f['estado'], f['ejecucion_codigo'] or 'Sin ejecución respaldada']
        for f in ocurrencias[:200]]
    ejecuciones_rows = [[e['codigo'], e['plan_codigo'], e['fecha_programada'],
        f'{e["fecha_inicio"]} – {e["fecha_fin"]}', e['ubicacion'], e['resultado'],
        e['responsable'], e['estado_display']] for e in ejecuciones[:200]]
    return [
        _tabla('Cobertura del alcance del mantenimiento de infraestructura',
            ['Espacio', 'Nombre', 'Situación documental'], espacios_rows,
            'Sin espacios individuales configurados. El plan debe confirmar expresamente su alcance para toda la unidad '
            'o justificar y respaldar la no aplicación anual.'),
        _tabla('Planes y alcance anual del mantenimiento de infraestructura',
            ['Código', 'Documento', 'Fecha del registro', 'Ubicación / intervención o justificación',
             'Criticidad', 'Responsable', 'Primera fecha programada', 'Frecuencia', 'Respaldo'],
            planes_rows, 'Sin plan ni declaración respaldada de no aplicación. Registra el alcance y su calendario.'),
        _tabla('Calendario anual declarado de infraestructura',
            ['Plan', 'Ubicación', 'Intervención', 'Criticidad', 'Fecha programada', 'Responsable',
             'Situación al corte', 'Informe de ejecución'], ocurrencias_rows,
            'Sin intervenciones programadas; no se presume mantenimiento realizado.'),
        _tabla('Informes de ejecución del mantenimiento de infraestructura',
            ['Informe', 'Plan', 'Ocurrencia programada', 'Inicio – fin reales', 'Ubicación', 'Resultado',
             'Responsable', 'Respaldo'], ejecuciones_rows,
            'Sin ejecuciones documentadas de mantenimiento de infraestructura.'),
    ]


def _tablas_funcionalidad(unidad, desde, hasta, estado, buscar):
    datos = _funcionalidad(unidad, desde, hasta, estado, buscar)
    ultimas = [[f'{f["codigo_equipo"]} · {f["nombre_equipo"]}',
        f'{_fecha(f["fecha"])} · {f["codigo"]}' if f['fecha'] else 'Sin prueba verificada',
        f['resultado'], f['responsable'] or 'Sin comprobación',
        'Del período consultado' if f['vigente_en_periodo'] else
        'Prueba anterior; falta comprobación de este período' if f['fecha'] else 'Sin prueba documentada al corte',
        f['seguimiento']] for f in datos['ultimas'][:200]]
    registros = [[f['codigo'], f'{f["codigo_equipo"]} · {f["nombre_equipo"]}', _fecha(f['fecha']),
        f['procedimiento'], f['criterio'], f['resultado'], f['hallazgos'] or 'Sin hallazgos declarados',
        f['responsable'], f['estado_display']] for f in datos['filas'][:200] if f['estado'] != 'anulado']
    return [
        _tabla('Última comprobación funcional real por equipo al corte',
            ['Equipo', 'Última prueba / referencia', 'Resultado documentado', 'Responsable',
             'Tramo de la comprobación', 'Seguimiento'], ultimas,
            'Sin equipos activos en esta selección. La disponibilidad no acredita una prueba funcional.'),
        _tabla('Pruebas funcionales documentadas en el período',
            ['Registro', 'Equipo', 'Fecha', 'Procedimiento o prueba', 'Criterio de aceptación',
             'Resultado', 'Hallazgos', 'Responsable', 'Estado del respaldo'], registros,
            'Sin pruebas funcionales documentadas en el período. Registra la comprobación realizada y su archivo.'),
    ]


def tablas_condiciones(category, unit, start_date, end_date, state='', search=''):
    """Tablas de detalle para el mismo informe HTML, PDF y hoja de cálculo."""
    if category == 'seguridad':
        return _tablas_seguridad(unit, start_date, end_date)
    if category == 'desechos':
        return _tablas_desechos(unit, start_date, end_date, state, search)
    if category in ('recursos', 'equipamiento'):
        tablas = _tablas_inventario(unit, start_date, end_date, search, state)
        if category == 'equipamiento' and es_unidad_auditable(unit):
            tablas = _tablas_funcionalidad(unit, start_date, end_date, state, search) + tablas
        return tablas
    if category == 'inventario':
        return _tablas_insumos(unit, search)
    if category == 'mantenimiento':
        return _tablas_mantenimiento(unit, start_date, end_date, state, search)
    return []


def documentos_condiciones(category, unit, start_date, end_date):
    """El visor usa la misma descarga protegida que las evidencias de gestión."""
    if category == 'mantenimiento' and es_unidad_auditable(unit):
        from apps.documentos.presentation.infraestructura_laboratorios import infraestructura_documentada
        datos = infraestructura_documentada(unit, date(start_date.year, 1, 1), date(start_date.year, 12, 31))
        return [f for f in datos['planes'] + datos['ejecuciones']
                if f['estado'] != 'anulado' and (f.get('recurso') or f.get('enlace'))][:200]
    if category == 'equipamiento' and es_unidad_auditable(unit):
        from apps.documentos.presentation.funcionalidad_laboratorios import funcionalidad_documentada
        datos = funcionalidad_documentada(unit, start_date, end_date)
        fuentes = {f['pk']: f for f in datos['filas'] + datos['ultimas']
                   if f['pk'] and f['estado'] != 'anulado' and f['recurso']}
        return list(fuentes.values())[:200]
    if category != 'seguridad':
        return []
    return [fila for fila in _inspecciones(unit, start_date, end_date)
            if fila.get('recurso') or fila.get('enlace')][:200]


def acciones_condiciones(category, unit, start_date, end_date):
    """Accesos directos para completar evidencias sin buscar otro módulo."""
    if category == 'mantenimiento' and es_unidad_auditable(unit):
        from apps.documentos.presentation.infraestructura_laboratorios import acciones_infraestructura
        return acciones_infraestructura(unit, start_date, end_date)
    if category == 'equipamiento' and es_unidad_auditable(unit):
        from apps.documentos.presentation.funcionalidad_laboratorios import acciones_funcionalidad
        return acciones_funcionalidad(unit, start_date, end_date)
    tipo = {'seguridad': 'INSPECCION', 'recursos': 'INVENTARIO', 'equipamiento': 'INVENTARIO',
            'desechos': 'DESECHOS'}.get(category)
    if not tipo:
        return []
    consulta = urlencode({'anio': start_date.year, 'corte': 'B' if start_date.month >= 7 else 'A', 'tipo': tipo})
    return [{'label': 'Registrar inspección y respaldo' if tipo == 'INSPECCION' else
             'Registrar acta de inventario' if tipo == 'INVENTARIO' else 'Registrar conciliación de desechos',
             'url': reverse('fuentes_metas_unidad', args=[unit.slug]) + '?' + consulta}]


def notas_condiciones(category):
    return {
        'seguridad': [
            'Los ingresos acreditan controles de acceso registrados. El protocolo, las inducciones y las '
            'inspecciones son evidencias diferentes; ninguna se presume a partir de las otras.',
            'Las listas de chequeo históricas se muestran si están registradas, aunque el catálogo las '
            'haya retirado como entrega independiente. Su ausencia se mantiene visible.',
            'Las inspecciones nuevas conservan área, condiciones revisadas, hallazgos, acción y plazo, '
            'responsable y respaldo. Un registro verificado no equivale por sí solo a un permiso de operación; '
            'las restricciones declaradas y las acciones pendientes se muestran expresamente.',
            'Los requisitos de acceso reflejan la configuración actual; la vigencia de las habilitaciones '
            'se consulta hasta la fecha final o hasta hoy si el período aún no termina.',
        ],
        'desechos': [
            'Se incluyen generaciones y entregas del período, y desechos anteriores que permanecen almacenados '
            'al corte. Las cantidades generadas se totalizan por separado en kg, litros y unidades.',
            'La clave del listado, autorización del gestor, licencia, manifiesto y respaldo se declaran '
            'en el registro. Mostrar estos datos no certifica su validez normativa ni la recepción final.',
            'La etapa y las observaciones son el estado registrado actualmente; una entrega posterior '
            'a la fecha de corte no se cuenta como entregada en ese período.',
        ],
        'recursos': [
            'El inventario muestra los recursos y su estado actuales. Las actas del período acreditan '
            'la revisión registrada; los datos de demostración no sustituyen evidencia institucional.',
        ],
        'equipamiento': [
            'La disponibilidad se calcula con los cambios de estado registrados. El estado actual '
            'y la verificación física del inventario se presentan aparte y no sustituyen una prueba técnica.',
            'En las unidades auditables cada comprobación funcional conserva equipo, procedimiento, criterio de aceptación, '
            'resultado, hallazgos, responsable y archivo. Se muestra la última prueba real verificada al corte; '
            'si pertenece a un período anterior, no se presenta como una comprobación de este período. '
            'Los ejemplos y borradores se identifican y no acreditan funcionalidad.',
        ],
        'inventario': [
            'Los movimientos corresponden al período consultado. Las tablas de existencias, '
            'lotes y vencimientos muestran el estado actual del inventario, con cantidades '
            'separadas por artículo y unidad de medida; no reconstruyen automáticamente un corte físico pasado.',
            'La coincidencia entre saldo y lotes es una conciliación de registros, no una verificación '
            'física. Las hojas de seguridad y requisitos de almacenamiento deben respaldarse cuando correspondan.',
        ],
        'mantenimiento': [
            'Las órdenes, sus ejecuciones, repuestos y costos corresponden al período de programación '
            'consultado. Estado, garantía y planes activos describen la situación actual del equipo.',
            'El resumen de equipos corresponde a su asignación actual. El detalle de órdenes conserva '
            'la unidad responsable de la intervención, incluso si posteriormente se trasladó el equipo.',
            'El cronograma muestra las próximas fechas proyectadas por frecuencia; no crea órdenes. '
            'Los días de intervención usan las fechas reales de órdenes completadas del período, '
            'recortadas al tramo consultado y sin duplicar intervalos superpuestos.',
            'Sin órdenes programadas no hay base para calcular cumplimiento. Un registro completado '
            'debe conservar resultado, responsable y archivo de informe para sustentar su ejecución.',
            'En las unidades auditables la meta del 80 % considera las intervenciones críticas exigibles del programa anual '
            'de equipos e infraestructura. El calendario futuro sigue dentro de plazo; las inspecciones de '
            'seguridad no sustituyen un plan ni un informe de mantenimiento. La ejecución operativa de órdenes '
            'se muestra aparte y no prueba el respaldo documental de la meta.',
            'Si no existen equipos críticos, el universo debe revisarse con un acta de inventario real y '
            'respaldada. El alcance de infraestructura se documenta con su plan o una declaración anual '
            'justificada de no aplicación. La ausencia de órdenes o de planes no concede cumplimiento.',
        ],
    }.get(category, [])
