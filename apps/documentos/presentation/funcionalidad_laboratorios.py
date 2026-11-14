"""Pruebas funcionales con respaldo propio, sin inferencias de disponibilidad."""
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.urls import reverse

from apps.documentos.models.funcionalidad import RESULTADOS_FUNCIONALES, equipos_del_alcance
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.models.respaldo_medicion import corte_efectivo
from apps.documentos.models.resultados_gestion import huella_resultado
from apps.documentos.presentation.perfil_unidades import es_unidad_auditable


def _fila(evidencia, verificadas, demo_global):
    detalle = evidencia.detalle if isinstance(evidencia.detalle, dict) else {}
    snapshot = detalle.get('equipo_snapshot') if isinstance(detalle.get('equipo_snapshot'), dict) else {}
    resultado = detalle.get('resultado_funcional') if isinstance(detalle.get('resultado_funcional'), str) else ''
    verificada = evidencia.pk in verificadas
    demo = bool(evidencia.demostracion or demo_global)
    return dict(pk=evidencia.pk, evidencia_id=evidencia.pk, codigo=evidencia.codigo, fecha=evidencia.fecha,
        titulo=evidencia.titulo, descripcion=evidencia.descripcion, responsable=str(evidencia.responsable),
        responsable_id=evidencia.responsable_id, equipo_id=detalle.get('equipo_id') if type(detalle.get('equipo_id')) is int else None,
        codigo_equipo=snapshot.get('codigo', ''), nombre_equipo=snapshot.get('nombre', ''),
        procedimiento=detalle.get('procedimiento', ''), prueba=detalle.get('procedimiento', ''),
        criterio=detalle.get('criterio', ''), resultado_funcional=resultado,
        resultado=dict(RESULTADOS_FUNCIONALES).get(resultado, 'Sin resultado documentado'),
        hallazgos=detalle.get('hallazgos_funcionales', ''), apto=resultado == 'operativo', no_apto=resultado == 'no_operativo',
        estado=evidencia.estado, estado_display='Rectificado' if evidencia.estado == 'anulado' else
            'Verificado · DEMO' if verificada and demo else 'Verificado' if verificada else
            'Verificación pendiente' if evidencia.estado == 'validado' else 'Borrador',
        verificada=verificada, acredita=verificada and not demo, demostracion=demo,
        recurso=evidencia.recurso_id, es_pdf=bool(evidencia.recurso_id and
            Path(evidencia.recurso.archivo.name).suffix.lower() == '.pdf'),
        sha256=evidencia.recurso.hash_sha256 if evidencia.recurso_id else '',
        contenido_sha256=huella_resultado(evidencia), enlace=evidencia.enlace, detalle=detalle)


def funcionalidad_documentada(unidad, inicio, fin):
    """Última comprobación real al corte y ausencia de pruebas del período, por equipo.

    El resultado se refiere al procedimiento y fecha registrados. No constituye
    autorización para operar ni cambia el estado del equipo. Una prueba antigua
    sigue disponible para consulta, sin presentarla como realizada este período.
    """
    if not es_unidad_auditable(unidad):
        return None
    from apps.documentos.presentation.medicion_metas import evidencias_verificadas, habilitada
    corte = corte_efectivo(unidad, fin)
    evidencias = list(EvidenciaGestionUnidad.objects.filter(unidad=unidad,
        tipo='FUNCIONALIDAD', fecha__lte=corte).select_related('recurso', 'responsable').order_by('fecha', 'pk'))
    verificadas = {e.pk for e in evidencias_verificadas(unidad, evidencias, inicio, corte)} if habilitada() else set()
    fuentes = [_fila(e, verificadas, getattr(settings, 'MEDICION_SOLO_DEMO', False)) for e in evidencias]
    filas = [f for f in fuentes if f['fecha'] >= inicio]
    por_equipo = {}
    for fila in fuentes:
        if fila['acredita'] and fila['equipo_id']:
            por_equipo[fila['equipo_id']] = fila
    ultimas = []
    equipos = equipos_del_alcance(unidad).filter(activa=True).select_related('equipo').order_by('codigo_unidad', 'pk')
    for equipo in equipos:
        if equipo.fecha_baja and equipo.fecha_baja <= corte:
            continue
        fuente = por_equipo.get(equipo.pk)
        vigente = bool(fuente and inicio <= fuente['fecha'] <= corte)
        fila = dict(fuente) if fuente else dict(pk=None, evidencia_id=None, codigo='', fecha=None,
            responsable='', responsable_id=None, titulo='', descripcion='', detalle={},
            procedimiento='', prueba='', criterio='', resultado_funcional='',
            resultado='Sin comprobación funcional documentada', hallazgos='', apto=False, no_apto=False,
            recurso=None, es_pdf=False, sha256='', contenido_sha256='', enlace='', estado='',
            estado_display='Sin comprobación', verificada=False, acredita=False, demostracion=False)
        fila.update(equipo_id=equipo.pk, codigo_equipo=equipo.codigo_unidad, nombre_equipo=equipo.equipo.nombre,
            estado_equipo=equipo.get_estado_unidad_display(), vigente_en_periodo=vigente,
            pendiente=not vigente, seguimiento='Sin prueba verificada del período' if not vigente else
                'Requiere atender hallazgos' if fuente['resultado_funcional'] != 'operativo' else
                'Operativo según la prueba documentada')
        ultimas.append(fila)
    return dict(filas=filas, ultimas=ultimas, pendientes=[f for f in ultimas if f['pendiente']],
        registrados=len(filas), verificados=sum(f['verificada'] for f in filas),
        reales=sum(f['acredita'] for f in filas), demostracion=sum(f['demostracion'] for f in filas),
        pendientes_verificacion=sum(f['estado'] != 'anulado' and not f['verificada'] for f in filas),
        universo_equipos=len(ultimas), comprobados_en_periodo=sum(f['vigente_en_periodo'] for f in ultimas),
        sin_comprobacion_periodo=sum(f['pendiente'] for f in ultimas),
        operativos=sum(f['vigente_en_periodo'] and f['apto'] for f in ultimas),
        observados=sum(f['vigente_en_periodo'] and f['resultado_funcional'] == 'observado' for f in ultimas),
        no_operativos=sum(f['vigente_en_periodo'] and f['no_apto'] for f in ultimas),
        desde=inicio.isoformat(), hasta=fin.isoformat(), corte=corte.isoformat())


def acciones_funcionalidad(unidad, inicio, fin):
    if not es_unidad_auditable(unidad):
        return []
    return [dict(label='Registrar verificación funcional de un equipo',
        url=reverse('fuentes_metas_unidad', args=[unidad.slug]) + '?' + urlencode(dict(
            anio=inicio.year, corte='B' if inicio.month >= 7 else 'A', tipo='FUNCIONALIDAD')))]
