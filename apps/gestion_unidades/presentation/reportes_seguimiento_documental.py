"""Consultas de seguimiento; reutilizan registros y no crean entregas ni notas."""
from datetime import date, datetime
from types import SimpleNamespace

from django.db.models import Prefetch, Q
from django.urls import reverse
from django.utils import timezone

from apps.documentos.models.expediente import DocumentoElaborado
from apps.documentos.models.mejora import AccionMejora, SeguimientoMejora
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo
from apps.recursos.presentation.ficha_equipo import AVISO_RETIRO, registros_baja_y_sustitucion


ESTADOS_RETIRO = (('sin_reemplazo', 'Retirado sin sustituto actual'),
                  ('con_reemplazo', 'Retirado con sustituto actual'),
                  ('sustituto', 'Equipo sustituto en el inventario actual'),
                  ('historial', 'Evento histórico; sin retiro o sustitución actual'))
ESTADOS_MEJORA = (('declarada', 'Acción declarada; cierre no verificado'),
                  ('pendiente', 'Acción formal dentro de plazo al corte'),
                  ('vencida', 'Acción formal vencida al corte'),
                  ('cerrada', 'Cierre formal con seguimiento registrado'),
                  ('sin_cierre_verificado', 'Cierre formal sin seguimiento de cierre'))
LIMITE = 500


def _dia(valor):
    if isinstance(valor, datetime):
        return timezone.localdate(valor) if timezone.is_aware(valor) else valor.date()
    return valor if isinstance(valor, date) else None


def _fecha(valor):
    if isinstance(valor, datetime):
        valor = timezone.localtime(valor) if timezone.is_aware(valor) else valor
        return valor.strftime('%d/%m/%Y %H:%M')
    return valor.strftime('%d/%m/%Y') if isinstance(valor, date) else str(valor or 'Sin registrar')


def _actor(usuario):
    return (usuario.get_full_name() or usuario.get_username()) if usuario else 'No registrado'


def _contiene(busqueda, *valores):
    return not busqueda or busqueda in ' '.join(str(v or '') for v in valores).casefold()


def _tabla(titulo, headers, rows):
    return dict(titulo=titulo, headers=headers, rows=rows[:LIMITE], vacio='Sin registros para esta selección.')


def _dataset(headers, rows, cards, choices, tablas, notes):
    return dict(headers=headers, rows=rows[:LIMITE], cards=cards, state_choices=choices,
        tablas=[_tabla(t['titulo'], t['headers'], t['rows']) for t in tablas], notes=notes,
        supporting_documents=[], matrix=False, matrix_kind='', structured=False, records=[],
        document_meta={}, column_count=len(headers),
        truncated=len(rows) > LIMITE or any(len(t['rows']) > LIMITE for t in tablas))


def reporte_retiros(unit, start_date, end_date, state='', search=''):
    """Hechos del rango y retiros previos todavía sin sustituto actual.

    Las relaciones actuales no tienen fecha estructurada de efectividad; no
    se reconstruye una sustitución histórica a partir de ese dato mutable.
    Los eventos conservan la unidad donde fueron registrados.
    """
    corte = min(end_date, timezone.localdate())
    estado = state if state in dict(ESTADOS_RETIRO) else ''
    buscar = str(search or '').strip().casefold()
    actuales = set(UnidadEquipo.objects.filter(Q(laboratorio=unit) | Q(laboratorios=unit))
        .values_list('pk', flat=True)) if start_date <= corte else set()
    equipos = list(UnidadEquipo.objects.filter(pk__in=actuales)
        .select_related('equipo', 'laboratorio').order_by('codigo_unidad')) if actuales else []
    registros = registros_baja_y_sustitucion(e for e in equipos if e.pk in actuales)
    eventos_historicos = {}
    if start_date <= corte:
        for evento in (EventoCicloVidaEquipo.objects.filter(unidad=unit, fecha__date__range=(start_date, corte))
                .exclude(equipo_id__in=actuales)
                .filter(Q(tipo__in=('baja', 'disposicion'))
                        | Q(tipo='actualizacion', descripcion__startswith='Retiro/sustitución: '))
                .select_related('usuario').order_by('fecha', 'pk')):
            eventos_historicos.setdefault(evento.equipo_id, []).append(evento)
    equipos.extend(SimpleNamespace(pk=clave) for clave in sorted(eventos_historicos))
    filas, hechos, cadenas, consultas = [], [], [], []
    estados = []
    for equipo in equipos:
        if equipo.pk not in actuales:
            # La unidad conserva su propio hecho histórico, no acceso a la
            # ficha mutable del activo transferido. No existe snapshot de la
            # identidad: sólo se muestra la referencia inmutable del activo.
            eventos = eventos_historicos.get(equipo.pk, [])
            referencia = f'Activo histórico ID {equipo.pk}'
            if not eventos or estado and estado != 'historial' or not _contiene(buscar,
                    referencia, *[f'{e.descripcion} {_actor(e.usuario)} {e.evidencia.name if e.evidencia else ""}'
                                  for e in eventos]):
                continue
            estados.append('historial')
            filas.append([referencia, 'Sin reconstrucción histórica', 'Sólo consta en los eventos propios',
                'Ficha actual fuera del alcance de esta unidad', 'Consultar el historial del rango',
                len(eventos), dict(ESTADOS_RETIRO)['historial']])
            hechos.extend([referencia, _fecha(e.fecha), _actor(e.usuario), e.descripcion,
                e.evidencia.name.rsplit('/', 1)[-1] if e.evidencia else 'Sin adjunto registrado'] for e in eventos)
            consultas.append([referencia, 'Sin acceso a la ficha actual desde esta unidad',
                              'Sólo los eventos históricos propios del rango'])
            continue
        registro = registros[equipo.pk]
        actuales_de_unidad = equipo.pk in actuales
        # Una transferencia no expone hechos registrados por otras unidades.
        historia = [h for h in registro['historial']
            if h['evento'].unidad_id == unit.pk
            or h['evento'].unidad_id is None and actuales_de_unidad]
        del_rango = [h for h in historia if start_date <= _dia(h['fecha']) <= corte]
        fecha = registro['fecha']
        retiro_del_rango = bool(fecha and start_date <= fecha <= corte
            and (actuales_de_unidad or historia))
        anterior_pendiente = bool(fecha and fecha < start_date and not registro['reemplazo']
            and (actuales_de_unidad or historia))
        reemplazados_visibles = [e for e in registro['reemplazados']
                                if e.laboratorio_id == unit.pk or e.pk in actuales]
        sustituidos = [e for e in reemplazados_visibles
                      if e.fecha_baja and start_date <= e.fecha_baja <= corte]
        if not (del_rango or retiro_del_rango or anterior_pendiente or sustituidos):
            continue
        clave = ('con_reemplazo' if registro['reemplazo'] else 'sin_reemplazo') if fecha else (
            'sustituto' if reemplazados_visibles else 'historial')
        if estado and clave != estado:
            continue
        reemplazo = registro['reemplazo']
        reemplazo_visible = bool(reemplazo and reemplazo.pk in actuales)
        sustituto = (f'{reemplazo.codigo_unidad} · {reemplazo.equipo.nombre}' if reemplazo_visible
            else f'Referencia de sustituto ID {reemplazo.pk}; ficha fuera del alcance'
            if reemplazo else 'Sin sustituto registrado')
        if not _contiene(buscar, equipo.codigo_unidad, equipo.equipo.nombre, equipo.codigo_bien,
                registro['motivo'], registro['justificacion'], sustituto,
                *[e.codigo_unidad for e in reemplazados_visibles],
                *[f'{h["descripcion"]} {_actor(h["usuario"])} {h["respaldo"]}' for h in del_rango]):
            continue
        estados.append(clave)
        filas.append([f'{equipo.codigo_unidad} · {equipo.equipo.nombre}', _fecha(fecha),
            registro['motivo'] if fecha else 'Sin retiro actual', sustituto if fecha else
            ('Sustituye a: ' + ', '.join(e.codigo_unidad for e in reemplazados_visibles)
             if reemplazados_visibles else 'Sin relación actual'),
            registro['justificacion'] or 'Sin referencia registrada', len(del_rango), dict(ESTADOS_RETIRO)[clave]])
        if fecha:
            cadenas.append([equipo.codigo_unidad, _fecha(fecha),
                reemplazo.codigo_unidad if reemplazo_visible else
                f'Referencia ID {reemplazo.pk}; fuera del alcance' if reemplazo else 'Sin sustituto registrado',
                equipo.laboratorio.nombre if equipo.laboratorio_id else 'Sin unidad principal',
                'Inventario actual; no fecha histórica de sustitución'])
        for anterior in sustituidos:
            cadenas.append([anterior.codigo_unidad, _fecha(anterior.fecha_baja), equipo.codigo_unidad,
                equipo.laboratorio.nombre if equipo.laboratorio_id else 'Sin unidad principal',
                'Relación actual del inventario'])
        hechos.extend([equipo.codigo_unidad, _fecha(h['fecha']), _actor(h['usuario']),
                       h['descripcion'], h['respaldo'] or 'Sin adjunto registrado'] for h in del_rango)
        ruta = (reverse('ficha_equipo_unidad_pdf', args=[unit.slug, equipo.pk]) + '?documento=baja'
                if actuales_de_unidad else 'Evento histórico de esta unidad; ficha actual fuera de su alcance')
        consultas.append([equipo.codigo_unidad, ruta,
            'Requiere permiso de recursos o mantenimiento de la unidad consultada'])
    return _dataset(
        ['Equipo', 'Fecha de retiro actual', 'Motivo actual', 'Sustitución actual',
         'Referencia / justificación actual', 'Eventos del rango', 'Situación actual'], filas,
        [('Activos seleccionados', len(filas)), ('Sin sustituto actual', estados.count('sin_reemplazo')),
         ('Con sustituto actual', estados.count('con_reemplazo')),
         ('Eventos registrados en el rango', len(hechos))], ESTADOS_RETIRO,
        [dict(titulo='Eventos de retiro y sustitución registrados en el rango',
              headers=['Equipo', 'Registrado el', 'Registrado por', 'Hecho registrado', 'Adjunto registrado'], rows=hechos),
         dict(titulo='Relaciones de sustitución del inventario actual',
              headers=['Activo anterior', 'Retiro actual', 'Sustituto actual', 'Unidad principal actual', 'Alcance'],
              rows=list(dict.fromkeys(tuple(fila) for fila in cadenas))),
         dict(titulo='Consultar el registro individual de retiro y sustitución',
              headers=['Equipo', 'PDF del registro', 'Acceso'], rows=consultas)],
        [AVISO_RETIRO,
         'El rango selecciona retiros y eventos registrados; también conserva retiros anteriores todavía sin sustituto en el inventario actual.',
         'Fecha, motivo, referencia y relaciones de sustitución son los datos actuales; los eventos del rango no reconstruyen por sí solos todo el inventario histórico.',
         'Un activo transferido fuera de esta unidad conserva sólo sus eventos propios y una referencia ID; su código, nombre y ficha actuales no se muestran ni se utilizan en la búsqueda.',
         'Una referencia o adjunto registrado no confirma su contenido ni una autorización patrimonial. La consulta no genera entrega, nota ni una obligación semestral.',
         f'Hechos consultados hasta {_fecha(corte)}. Los filtros de búsqueda y situación seleccionan los mismos activos en el listado y sus detalles.'])


def _plazo(valor):
    try:
        return date.fromisoformat(str(valor))
    except (ValueError, TypeError):
        return None


def reporte_mejora(unit, start_date, end_date, state='', search=''):
    """Acciones declaradas y formales, con pendientes anteriores aún abiertos al corte."""
    from apps.documentos.presentation.expediente import cortes_del_anio, tramo_del_documento

    corte = min(end_date, timezone.localdate())
    estado = state if state in dict(ESTADOS_MEJORA) else ''
    buscar = str(search or '').strip().casefold()
    filas, declaradas, seguimientos, decisiones, claves = [], [], [], [], []
    formales = (AccionMejora.objects.filter(informe__unidad=unit, creada_en__date__lte=corte)
        .filter(Q(cerrada_en__isnull=True) | Q(cerrada_en__date__gte=start_date))
        .select_related('responsable', 'informe__recurso')
        .prefetch_related(Prefetch('seguimientos', queryset=SeguimientoMejora.objects.filter(
            creado_en__date__lte=corte).select_related('creado_por').order_by('creado_en', 'pk')))
        .order_by('vence_el', 'pk')) if start_date <= corte else []
    for accion in formales:
        avances = list(accion.seguimientos.all())
        cerrada = bool(accion.cerrada_en and _dia(accion.cerrada_en) <= corte)
        con_seguimiento_cierre = cerrada and any(s.cierre and s.creado_por_id for s in avances)
        clave = ('cerrada' if con_seguimiento_cierre else 'sin_cierre_verificado') if cerrada else (
            'vencida' if accion.vence_el < corte else 'pendiente')
        origen = f'{accion.informe.anio}-{accion.informe.corte or "Anual"}'
        if estado and clave != estado or not _contiene(buscar, accion.pk, accion.descripcion,
                _actor(accion.responsable), origen, accion.informe.motivo,
                *[s.detalle for s in avances]):
            continue
        referencia = f'AM-{accion.pk}'
        claves.append(clave)
        ultimo = avances[-1] if avances else None
        filas.append([f'Formal · {referencia}', accion.descripcion, _actor(accion.responsable),
            _fecha(accion.vence_el), dict(ESTADOS_MEJORA)[clave],
            f'Cierre actual: {_fecha(accion.cerrada_en)}' if accion.cerrada_en else 'Actualmente abierta',
            f'{_fecha(ultimo.creado_en)} · {ultimo.detalle}' if ultimo else 'Sin seguimiento al corte', origen])
        seguimientos.extend([referencia, _fecha(s.creado_en), _actor(s.creado_por), s.detalle,
            'Seguimiento marcado como cierre' if s.cierre else 'Avance registrado; no acredita cierre',
            'En el rango' if _dia(s.creado_en) >= start_date else 'Antecedente anterior al rango'] for s in avances)
        decision_al_corte = bool(accion.informe.decidido_en and _dia(accion.informe.decidido_en) <= corte)
        recurso = accion.informe.recurso
        respaldo = ('Documento de origen de otra unidad; no se enlaza' if recurso.unidad_id != unit.pk else
            'Documento de origen inactivo u obsoleto; no se enlaza' if not recurso.activo or recurso.estado != 'vigente' else
            reverse('recurso_unidad', args=[recurso.pk]) if recurso.archivo else 'Sin archivo de origen registrado')
        decisiones.append([referencia, origen, accion.informe.get_decision_display() if decision_al_corte else
            'Sin decisión registrada al corte', _fecha(accion.informe.decidido_en) if decision_al_corte else '—',
            respaldo])
    redacciones = (DocumentoElaborado.objects.filter(documento__unidad=unit,
        documento__exigido__fuente_reporte='informe', documento__anio__lte=corte.year,
        actualizado_en__date__lte=corte).select_related('documento__exigido', 'documento__unidad')
        .order_by('documento__anio', 'documento__corte', 'pk')) if start_date <= corte and estado in ('', 'declarada') else []
    cortes = {}
    for redaccion in redacciones:
        contenido = redaccion.contenido if isinstance(redaccion.contenido, dict) else {}
        acciones = contenido.get('acciones') if isinstance(contenido.get('acciones'), list) else []
        if not acciones:
            continue
        documento = redaccion.documento
        if documento.anio not in cortes:
            cortes[documento.anio] = cortes_del_anio(documento.anio)
        inicio_doc, fin_doc = tramo_del_documento(documento, cortes[documento.anio])
        informe_del_rango = inicio_doc <= corte and fin_doc >= start_date
        for numero, accion in enumerate(acciones, 1):
            if not isinstance(accion, dict):
                continue
            plazo = _plazo(accion.get('plazo'))
            declaracion = str(accion.get('estado') or '')
            if not (informe_del_rango or plazo and start_date <= plazo <= corte
                    or declaracion != 'cumplida' and (not plazo or plazo <= corte)):
                continue
            if not _contiene(buscar, accion.get('hallazgo'), accion.get('accion'), accion.get('responsable'),
                             documento.etiqueta_corte, accion.get('estado')):
                continue
            referencia = f'DOC-{documento.pk}/{numero}'
            claves.append('declarada')
            estado_declarado = {'pendiente': 'Pendiente declarada', 'en_curso': 'En curso declarada',
                'cumplida': 'Cumplida declarada; sin cierre verificado'}.get(declaracion, 'Estado no definido en el editor')
            filas.append([f'Declarada · {referencia}', str(accion.get('accion') or 'Sin acción descrita'),
                str(accion.get('responsable') or 'Sin responsable declarado'), _fecha(plazo or accion.get('plazo')),
                dict(ESTADOS_MEJORA)['declarada'], estado_declarado,
                f'Redacción v{redaccion.version}; actualizada {_fecha(redaccion.actualizado_en)}', documento.etiqueta_corte])
            declaradas.append([referencia, documento.etiqueta_corte, str(accion.get('hallazgo') or 'Sin hallazgo declarado'),
                str(accion.get('accion') or 'Sin acción descrita'), str(accion.get('responsable') or 'Sin responsable declarado'),
                _fecha(plazo or accion.get('plazo')), estado_declarado])
    return _dataset(
        ['Origen / referencia', 'Acción', 'Responsable actual o declarado', 'Plazo', 'Situación al corte',
         'Estado actual o declarado', 'Seguimiento al corte / redacción', 'Documento de origen'], filas,
        [('Acciones seleccionadas', len(filas)), ('Declaradas sin cierre verificado', claves.count('declarada')),
         ('Formales vencidas al corte', claves.count('vencida')),
         ('Cierres con seguimiento registrado', claves.count('cerrada'))], ESTADOS_MEJORA,
        [dict(titulo='Acciones declaradas en el editor; no equivalen a cierre verificado',
              headers=['Referencia', 'Informe', 'Hallazgo', 'Acción', 'Responsable declarado', 'Plazo', 'Estado declarado'], rows=declaradas),
         dict(titulo='Avances y registros de cierre de las acciones formales seleccionadas al corte',
              headers=['Acción', 'Registrado el', 'Autor', 'Avance y respaldo declarado', 'Alcance del registro', 'Relación con el rango'], rows=seguimientos),
         dict(titulo='Decisiones y documentos de origen de las acciones formales seleccionadas',
              headers=['Acción', 'Período', 'Decisión al corte', 'Fecha de decisión', 'Documento'], rows=decisiones)],
        ['Las acciones declaradas en el editor y las acciones formales tienen referencias distintas; no se convierten entre sí ni se suman como porcentaje de cumplimiento.',
         'Una acción formal anterior continúa incluida si seguía abierta al corte, aunque actualmente se haya cerrado después. Un texto «cumplida» no equivale a cierre verificado.',
         'La consulta identifica si existe un seguimiento marcado como cierre. No certifica su autorización, su respaldo ni la eficacia de la acción; esas comprobaciones corresponden al circuito de seguimiento.',
         'Las declaraciones se leen de la redacción guardada antes del corte; una redacción actualizada después no permite reconstruir automáticamente su contenido histórico.',
         f'Consulta hasta {_fecha(corte)}; el responsable formal y el estado actual se identifican aparte del resultado al corte. Búsqueda y situación seleccionan las mismas acciones en todas las tablas.'])
