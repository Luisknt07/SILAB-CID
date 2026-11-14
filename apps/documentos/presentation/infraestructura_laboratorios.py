"""Programa y ejecución de infraestructura, separados de inspecciones y equipos."""
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.urls import reverse

from apps.documentos.models.infraestructura import (
    CRITICIDADES_INFRAESTRUCTURA, es_laboratorio_infraestructura, fecha_detalle,
)
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.models.respaldo_medicion import corte_efectivo
from apps.documentos.models.resultados_gestion import huella_resultado


def fechas_programadas(detalle, inicio, fin):
    """Expande únicamente las ocurrencias declaradas, sin crear registros."""
    primera = fecha_detalle(detalle, 'fecha_programada')
    ultima = fecha_detalle(detalle, 'fecha_fin_programacion')
    frecuencia = detalle.get('frecuencia_dias')
    if (not primera or not isinstance(frecuencia, int) or isinstance(frecuencia, bool)
            or not 0 <= frecuencia <= 3660 or inicio > fin):
        return
    fin = min(fin, ultima) if ultima else fin
    if not frecuencia:
        if inicio <= primera <= fin:
            yield primera
        return
    salto = max(0, ((inicio - primera).days + frecuencia - 1) // frecuencia)
    if salto * frecuencia > (fin - primera).days:
        return
    proxima = primera + timedelta(days=salto * frecuencia)
    while proxima <= fin:
        yield proxima
        # No desbordar date.max ante un período de consulta extremo.
        if (fin - proxima).days < frecuencia:
            break
        proxima += timedelta(days=frecuencia)


def _fuente(evidencia, verificadas, demo_global):
    detalle = evidencia.detalle if isinstance(evidencia.detalle, dict) else {}
    verificada = evidencia.pk in verificadas
    demo = bool(evidencia.demostracion or demo_global)
    estado_display = ('Rectificado' if evidencia.estado == 'anulado' else
        'Verificado · DEMO' if verificada and demo else 'Verificado' if verificada else
        'Verificación pendiente' if evidencia.estado == 'validado' else 'Borrador')
    criticidad = detalle.get('criticidad') if isinstance(detalle.get('criticidad'), str) else ''
    plan_id = detalle.get('plan_id') if type(detalle.get('plan_id')) is int else None
    return dict(pk=evidencia.pk, codigo=evidencia.codigo, fecha=evidencia.fecha,
        titulo=evidencia.titulo, estado=evidencia.estado, estado_display=estado_display,
        demostracion=demo, verificada=verificada, acredita=verificada and not demo,
        recurso=evidencia.recurso_id, es_pdf=bool(evidencia.recurso_id and
            Path(evidencia.recurso.archivo.name).suffix.lower() == '.pdf'),
        sha256=evidencia.recurso.hash_sha256 if evidencia.recurso_id else '',
        contenido_sha256=huella_resultado(evidencia), enlace=evidencia.enlace,
        detalle=detalle, responsable=str(evidencia.responsable),
        alcance_infraestructura=detalle.get('alcance_infraestructura', ''),
        justificacion_alcance=detalle.get('justificacion_alcance', ''),
        responsable_id=evidencia.responsable_id, descripcion=evidencia.descripcion,
        ubicacion=detalle.get('ubicacion', ''), espacio_id=detalle.get('espacio_id'),
        intervencion=detalle.get('intervencion', ''), criticidad=criticidad,
        criticidad_display=dict(CRITICIDADES_INFRAESTRUCTURA).get(criticidad, 'Sin definir'),
        fecha_programada=detalle.get('fecha_programada', ''), frecuencia_dias=detalle.get('frecuencia_dias'),
        fecha_fin_programacion=detalle.get('fecha_fin_programacion', ''),
        plan_id=plan_id, plan_codigo=detalle.get('plan_codigo', ''),
        fecha_inicio=detalle.get('fecha_inicio', ''), fecha_fin=detalle.get('fecha_fin', ''),
        resultado=detalle.get('resultado', ''))


def infraestructura_documentada(unidad, inicio, fin):
    """Cumplimiento de ocurrencias vencidas, con fuentes reales y pendientes visibles.

    Las fechas futuras se muestran como calendario, no como incumplimiento. La
    ausencia de un plan no equivale a que la unidad carezca de necesidades
    de mantenimiento: conserva `sin_plan` para advertir la falta de programación.
    """
    if not es_laboratorio_infraestructura(unidad):
        return None
    from apps.documentos.presentation.medicion_metas import evidencias_verificadas, habilitada
    corte = corte_efectivo(unidad, fin)
    planes_modelo = list(EvidenciaGestionUnidad.objects.filter(unidad=unidad, tipo='PLAN-INFRA',
        fecha__lte=corte).select_related('recurso', 'responsable').order_by('fecha', 'pk'))
    ejecuciones_modelo = list(EvidenciaGestionUnidad.objects.filter(unidad=unidad, tipo='EJECUCION-INFRA',
        fecha__range=(inicio, corte)).select_related('recurso', 'responsable').order_by('fecha', 'pk'))
    fuentes = planes_modelo + ejecuciones_modelo
    verificadas = {e.pk for e in evidencias_verificadas(unidad, fuentes, inicio, corte)} if habilitada() else set()
    demo_global = getattr(settings, 'MEDICION_SOLO_DEMO', False)
    planes = [_fuente(e, verificadas, demo_global) for e in planes_modelo]
    ejecuciones = [_fuente(e, verificadas, demo_global) for e in ejecuciones_modelo]
    planes_por_id = {p['pk']: p for p in planes}
    cierres = {}
    for ejecucion in ejecuciones:
        plan = planes_por_id.get(ejecucion['plan_id'])
        ejecucion['acredita'] = bool(ejecucion['acredita'] and plan and plan['acredita'])
        if ejecucion['acredita']:
            cierres.setdefault((ejecucion['plan_id'], ejecucion['fecha_programada']), ejecucion)
    ocurrencias, futuras = [], []
    for plan in planes:
        if plan['estado'] == 'anulado' or plan['alcance_infraestructura'] == 'no_aplica':
            continue
        for prevista in fechas_programadas(plan['detalle'], inicio, fin):
            cierre = cierres.get((plan['pk'], prevista.isoformat())) if prevista <= corte else None
            fila = dict(plan_id=plan['pk'], plan_codigo=plan['codigo'], ubicacion=plan['ubicacion'],
                espacio_id=plan['espacio_id'], intervencion=plan['intervencion'],
                criticidad=plan['criticidad'], responsable=plan['responsable'],
                fecha_programada=prevista.isoformat(), plan_verificado=plan['verificada'],
                demostracion=plan['demostracion'], acredita=bool(cierre),
                ejecucion_id=cierre['pk'] if cierre else None,
                ejecucion_codigo=cierre['codigo'] if cierre else '',
                estado='Ejecución respaldada' if cierre else 'Programada: dentro de plazo' if prevista > corte else
                       'Plan sin verificar' if not plan['verificada'] else 'Demostración: no acredita' if plan['demostracion'] else
                       'Pendiente de ejecución respaldada')
            (futuras if prevista > corte else ocurrencias).append(fila)
    # Los ejemplos y borradores se ven en el informe, pero no modifican el universo real verificado.
    exigibles = [f for f in ocurrencias if f['plan_verificado'] and not f['demostracion']]
    acreditadas = sum(f['acredita'] for f in exigibles)
    pendientes = [f for f in ocurrencias if not f['acredita']]
    planes_reales = [p for p in planes if p['acredita']]
    planes_aplicables = [p for p in planes_reales if p['alcance_infraestructura'] == 'aplica' and
        next(fechas_programadas(p['detalle'], date(inicio.year, 1, 1), date(fin.year, 12, 31)), None)]
    declaraciones_no_aplica = [p for p in planes_reales if p['alcance_infraestructura'] == 'no_aplica' and
        inicio.year <= p['fecha'].year <= fin.year]
    contradiccion = bool(planes_aplicables and declaraciones_no_aplica)
    from apps.gestion_unidades.models.espacios import EspacioReservable
    espacios = list(EspacioReservable.objects.filter(unidad=unidad, activo=True).order_by('pk').values('pk', 'codigo', 'nombre'))
    cubiertos, declaracion_global = set(), False
    for plan in planes_aplicables:
        detalle = plan['detalle']
        if type(plan['espacio_id']) is int:
            cubiertos.add(plan['espacio_id'])
        if detalle.get('alcance_todo_laboratorio') is True:
            declaracion_global = True
            registrados = detalle.get('espacios_alcance')
            if isinstance(registrados, list):
                cubiertos.update(pk for pk in registrados if type(pk) is int)
    espacios_sin_cobertura = ([e for e in espacios if e['pk'] not in cubiertos]
        if not declaraciones_no_aplica or contradiccion else [])
    cobertura_completa = bool(planes_aplicables and not espacios_sin_cobertura and (espacios or declaracion_global))
    alcance_declarado = bool(cobertura_completa or declaraciones_no_aplica) and not contradiccion
    no_aplica = bool(declaraciones_no_aplica) and not contradiccion
    fuentes_alcance = [dict(pk=p['pk'], codigo=p['codigo'], anio=p['fecha'].year,
        alcance=p['alcance_infraestructura'], justificacion=p['justificacion_alcance'],
        espacio_id=p['espacio_id'], alcance_todo_laboratorio=p['detalle'].get('alcance_todo_laboratorio') is True,
        espacios_alcance=p['detalle'].get('espacios_alcance', []),
        contenido_sha256=p['contenido_sha256'], sha256=p['sha256'])
        for p in planes_aplicables + declaraciones_no_aplica]
    return dict(planes=planes, ejecuciones=ejecuciones, ocurrencias=ocurrencias, futuras=futuras,
        programadas=len(exigibles), acreditadas=acreditadas, numerador=acreditadas, denominador=len(exigibles),
        pendientes=pendientes, sin_plan=not alcance_declarado,
        alcance_declarado=alcance_declarado, no_aplica=no_aplica, alcance_contradictorio=contradiccion,
        justificacion=declaraciones_no_aplica[-1]['justificacion_alcance'] if declaraciones_no_aplica else '',
        fuentes_alcance=fuentes_alcance, espacios_sin_cobertura=espacios_sin_cobertura,
        espacios_del_laboratorio=espacios, cobertura_global_declarada=declaracion_global,
        espacios_de_la_unidad=espacios,
        planes_sin_verificar=sum(p['estado'] != 'anulado' and not p['verificada'] for p in planes),
        ejecuciones_sin_verificar=sum(e['estado'] != 'anulado' and not e['acredita'] for e in ejecuciones),
        cobertura=round(100 * acreditadas / len(exigibles), 2) if exigibles else None,
        corte=corte.isoformat(), desde=inicio.isoformat(), hasta=fin.isoformat())


def acciones_infraestructura(unidad, inicio, fin):
    if not es_laboratorio_infraestructura(unidad):
        return []
    ruta = reverse('fuentes_metas_unidad', args=[unidad.slug])
    return [dict(label=etiqueta, url=ruta + '?' + urlencode(dict(anio=inicio.year,
        corte='B' if inicio.month >= 7 else 'A', tipo=tipo))) for tipo, etiqueta in (
            ('PLAN-INFRA', 'Programar mantenimiento de infraestructura'),
            ('EJECUCION-INFRA', 'Registrar ejecución de infraestructura'))]
