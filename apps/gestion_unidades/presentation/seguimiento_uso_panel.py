"""Alcance visible del seguimiento: disponibilidad, uso y compromiso separados."""
from datetime import date, timedelta
from calendar import monthrange
from urllib.parse import urlencode

from django.core.exceptions import ObjectDoesNotExist
from django.urls import NoReverseMatch, reverse


ALCANCES = (('semana', 'Esta semana'), ('mes', 'Este mes'),
            ('semestre', 'Este semestre'), ('anio', 'Este año'))


def rango_seguimiento(parametros, hoy):
    """Tramos naturales al corte de hoy; nunca se contabiliza el futuro."""
    seleccion = str((parametros or {}).get('seguimiento') or 'semestre')
    if seleccion not in dict(ALCANCES):
        seleccion = 'semestre'
    if seleccion == 'semana':
        inicio = hoy - timedelta(days=hoy.weekday())
    elif seleccion == 'mes':
        inicio = hoy.replace(day=1)
    elif seleccion == 'anio':
        inicio = date(hoy.year, 1, 1)
    else:
        inicio = date(hoy.year, 1 if hoy.month <= 6 else 7, 1)
    return seleccion, inicio, hoy


def _plan_para_seguimiento(unidad, hoy):
    from apps.documentos.models.expediente import DocumentoExpediente
    from apps.documentos.presentation.expediente import tramo_del_documento

    corte = 'A' if hoy.month <= 6 else 'B'
    documento = (DocumentoExpediente.objects.filter(unidad=unidad, anio=hoy.year,
        corte=corte, exigido__codigo='PLANIFICACION')
        .select_related('exigido', 'redaccion').order_by('-pk').first())
    if documento is None:
        return dict(documento=None, presupuesto=None, legado=False, contenido={})
    inicio, fin = tramo_del_documento(documento)
    natural = (date(hoy.year, 1, 1), date(hoy.year, 6, 30)) if corte == 'A' else (
        date(hoy.year, 7, 1), date(hoy.year, 12, 31))
    legado = documento.marco_periodo != 'gestion_v1' or (inicio, fin) != natural
    try:
        contenido = documento.redaccion.contenido or {}
    except ObjectDoesNotExist:
        contenido = {}
    if not isinstance(contenido, dict):
        contenido = {}
    presupuesto = contenido.get('presupuesto_uso')
    return dict(documento=documento, contenido=contenido, legado=legado,
                presupuesto=presupuesto if isinstance(presupuesto, dict) and not legado else None)


def contexto_seguimiento_uso(unidad, hoy, *, parametros=None, usuario=None):
    from apps.recursos.presentation.seguimiento_uso import seguimiento_uso_unidad
    from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad

    seleccion, inicio, fin = rango_seguimiento(parametros, hoy)
    corte = 'A' if hoy.month <= 6 else 'B'
    plan = _plan_para_seguimiento(unidad, hoy)
    presupuesto = plan['presupuesto'] if seleccion == 'semestre' else None
    if seleccion == 'semana':
        fin_natural = hoy + timedelta(days=6 - hoy.weekday())
    elif seleccion == 'mes':
        fin_natural = hoy.replace(day=monthrange(hoy.year, hoy.month)[1])
        mensual = (plan['presupuesto'] or {}).get('horas_por_mes')
        if isinstance(mensual, dict) and str(hoy.month) in mensual:
            presupuesto = dict(horas_comprometidas=mensual[str(hoy.month)],
                justificacion=plan['presupuesto'].get('justificacion', ''),
                horas_por_mes={str(hoy.month): mensual[str(hoy.month)]})
    elif seleccion == 'semestre':
        fin_natural = date(hoy.year, 6, 30) if hoy.month <= 6 else date(hoy.year, 12, 31)
    else:
        fin_natural = date(hoy.year, 12, 31)
    seguimiento = seguimiento_uso_unidad(unidad, inicio, fin_natural, presupuesto=presupuesto, hoy=hoy)
    seguimiento = dict(seguimiento)
    def presentar_medida(medida):
        dias = [d for d in medida.get('daily', []) if d.get('medido')]
        medida['horario_pendiente'] = (not all(d.get('jornada_conocida') for d in dias)
            if dias else medida.get('frequency_pending', True))
        medida['capacidad_pendiente'] = (not all(d.get('capacidad_conocida') and d.get('capacidad_respaldada')
            for d in dias if d.get('disponible_segundos'))
            if dias else medida.get('utilization_pending', True))
        return medida
    seguimiento['semestre'] = presentar_medida(dict(seguimiento['semestre']))
    etiquetas_fuentes = dict(horarios='Jornadas declaradas', capacidades='Registros de capacidad',
        bloqueos='Bloqueos aplicables', calendarios='Calendarios de referencia', atenciones='Ejecuciones efectivas')
    seguimiento['fuentes_interfaz'] = [dict(etiqueta=etiquetas_fuentes.get(k, k), cantidad=len(v))
        for k, v in seguimiento.get('fuentes', {}).items() if isinstance(v, (list, tuple, set))]
    consulta_base = reverse('gestion_unidad', args=[unidad.slug])
    extras = {k: '1' for k in ('modal', 'fragment') if str((parametros or {}).get(k, '')) == '1'}
    opciones = [dict(valor=valor, etiqueta=etiqueta, activa=valor == seleccion,
        url=consulta_base + '?' + urlencode(dict(view='indicadores', seguimiento=valor, **extras)))
        for valor, etiqueta in ALCANCES]
    documento = plan['documento']
    argumentos = dict(anio=hoy.year, corte=corte)
    if documento:
        argumentos['gestionar'] = documento.pk
    else:
        argumentos['gestionar'] = 'PLANIFICACION'
    url_expediente = reverse('gestion_expediente_unidad', args=[unidad.slug]) + '?' + urlencode(argumentos)
    acciones = []
    editable = usuario is not None and puede_operar_modulo_unidad(usuario, unidad, 'reportes')
    if documento and editable and documento.estado != 'validado':
        acciones.append(dict(etiqueta='Editar metas del semestre',
            url=reverse('redactar_documento_expediente', args=[unidad.slug, documento.pk]), editor=True))
    else:
        acciones.append(dict(etiqueta='Consultar metas del semestre' if documento else 'Definir metas del semestre',
                             url=url_expediente))
    if usuario is not None and (puede_operar_modulo_unidad(usuario, unidad, 'configuracion') or
                               puede_operar_modulo_unidad(usuario, unidad, 'agenda')):
        acciones.append(dict(etiqueta='Configurar aforo y jornadas',
            url=consulta_base + '?' + urlencode(dict(view='configuracion', **extras)), gestion=True))
    if usuario is not None and usuario.is_superuser:
        try:
            acciones.append(dict(etiqueta='Referencias de indicadores',
                                 url=reverse('admin:documentos_referenciaindicadorunidad_changelist')))
        except NoReverseMatch:
            pass  # La configuración se publica junto con su modelo administrativo.
    avisos = []
    if seleccion == 'anio':
        avisos.append('La meta se compromete por semestre. Esta consulta anual muestra uso real; no atribuye una meta anual a un solo plan.')
    elif plan['legado']:
        avisos.append('El plan conservado corresponde a un marco anterior. Sus metas no se aplican a fechas fuera de aquel documento; consulta sus compromisos en el expediente.')
    elif seleccion in ('semestre', 'mes') and not presupuesto:
        avisos.append('Falta definir el presupuesto de horas de uso en la planificación del semestre. La capacidad disponible y el uso real se muestran por separado de esa meta.')
    if documento and documento.estado != 'validado':
        avisos.append('Las metas de este plan siguen en edición; todavía no constituyen un compromiso enviado.')
    serie_base = seguimiento.get('semanas', []) if seleccion in ('semana', 'mes') else seguimiento.get('meses', [])
    serie = [f for f in serie_base if f['inicio'] <= hoy]
    for fila in serie:
        fila['fin_corte'] = min(fila['fin'], hoy)
        fila['medida'] = presentar_medida(dict(fila['medida']))
    seguimiento.update(seleccion=seleccion, opciones=opciones, inicio=inicio, fin=fin,
        titulo=dict(ALCANCES)[seleccion], semestre_etiqueta='I semestre · enero–junio' if corte == 'A' else 'II semestre · julio–diciembre',
        acciones=acciones, plan_url=url_expediente, avisos_panel=avisos,
        plan_enviado=bool(documento and documento.estado == 'validado'),
        plan_legado=plan['legado'], unidad=unidad,
        serie=serie,
        agrupacion='Semana' if seleccion in ('semana', 'mes') else 'Mes')
    return seguimiento
