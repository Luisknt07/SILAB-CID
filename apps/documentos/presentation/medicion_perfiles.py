"""Medidores de fuentes nativas: un estado publicado/cerrado no sustituye su revisión técnica."""
from datetime import date
import hashlib
import json
from pathlib import Path

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.documentos.models.resultados_perfiles import TIPOS_PERFIL, errores_perfil

BASES_PERFIL = ('observatorios', 'plantas_piloto', 'centro_experimental')
SUBTIPOS = {'BOLETINES': ('publicacion', 'datos'), 'EVENTOS': ('socializacion',),
            'PRODUCCION': ('produccion', 'control_calidad', 'sin_produccion'), 'ENSAYOS': ('ensayo',)}
ACTIVIDADES_PERFIL = {'publicacion': 'BOLETINES', 'datos': 'DATOS-ACTUALIZADOS',
                     'socializacion': 'EVENTOS', 'produccion': 'PRODUCCION',
                     'control_calidad': 'CONTROL-CALIDAD', 'sin_produccion': 'CONTROL-CALIDAD', 'ensayo': 'ENSAYOS'}


def base_perfil(unidad):
    return getattr(unidad, 'codigo_base', '')


def usa_contrato_perfil(unidad, tipo):
    return base_perfil(unidad) in BASES_PERFIL and tipo in TIPOS_PERFIL


def huella_nativa(datos):
    return hashlib.sha256(json.dumps(datos, sort_keys=True, default=str, ensure_ascii=True).encode()).hexdigest()


def _archivo(archivo):
    if not archivo:
        return ''
    try:
        archivo.open('rb')
        sha, total = hashlib.sha256(), 0
        for bloque in archivo.chunks():
            total += len(bloque)
            sha.update(bloque)
        if not total:
            raise ValueError
        return sha.hexdigest()
    except (OSError, ValueError) as exc:
        raise ValidationError('El archivo de origen no está disponible o está vacío.') from exc
    finally:
        archivo.close()


def _valores(objeto, campos):
    return {campo: getattr(objeto, campo) for campo in campos}


def _indicador(indicador, unidad):
    if indicador.unidad_id != unidad.pk or not indicador.publicado:
        raise ValidationError('El indicador debe estar publicado en este observatorio.')
    campos = ('codigo', 'nombre', 'definicion', 'formula', 'unidad_medida', 'fuente', 'periodicidad')
    if any(not str(getattr(indicador, c) or '').strip() for c in campos):
        raise ValidationError('Completa definición, fórmula, unidad, fuente y periodicidad del indicador.')
    return _valores(indicador, (*campos, 'url_fuente', 'limitaciones', 'territorio_principal'))


def _fecha_real(valor, fecha):
    if not valor or valor > fecha or valor > timezone.localdate():
        raise ValidationError('El registro de origen debe haber ocurrido a la fecha de la evidencia.')


def fotografia_nativa(unidad, tipo, detalle, fecha):
    """Relee las filas y el archivo reales. Nunca acepta una huella enviada por el navegador."""
    errores = errores_perfil(tipo, detalle, fecha)
    if errores:
        raise ValidationError(errores)
    subtipo = detalle['subtipo']
    base = base_perfil(unidad)
    if (tipo in ('BOLETINES', 'EVENTOS') and base != 'observatorios' or
            tipo == 'PRODUCCION' and base != 'plantas_piloto' or
            tipo == 'ENSAYOS' and base != 'centro_experimental'):
        raise ValidationError('Este registro no corresponde al tipo de unidad.')
    if subtipo == 'socializacion':
        _fecha_real(date.fromisoformat(detalle['fecha_evento']), fecha)
        return dict(subtipo=subtipo, fecha=detalle['fecha_evento'],
                    participantes=detalle['participantes'], beneficiario=detalle['beneficiario'],
                    referencia=detalle['referencia_acta'])
    if subtipo == 'sin_produccion':
        from apps.plantas_piloto.operacion.models.produccion import OrdenProduccion, LoteProducto
        desde, hasta = (date.fromisoformat(detalle[c]) for c in ('periodo_desde', 'periodo_hasta'))
        if OrdenProduccion.objects.filter(unidad=unidad, demostrativa=False, estado='terminada',
                cerrada_en__date__range=(desde, hasta)).exists() or LoteProducto.objects.filter(
                    unidad=unidad, demostrativo=False, fecha_produccion__range=(desde, hasta)).exists():
            raise ValidationError('Hay producción finalizada en el tramo: sus controles deben medirse y no corresponde declararlos no aplicables.')
        return dict(subtipo=subtipo, desde=desde, hasta=hasta,
                    justificacion=detalle['justificacion_sin_produccion'], ordenes_finalizadas=[])
    if subtipo == 'publicacion':
        from apps.observatorios.operacion.models.observatorios import PublicacionObservatorio
        item = PublicacionObservatorio.objects.filter(pk=detalle['publicacion_id'], unidad=unidad).first()
        if item is None or item.estado != 'publicada':
            raise ValidationError('Selecciona una publicación efectivamente publicada en este observatorio.')
        _fecha_real(item.fecha_publicada, fecha)
        if not item.archivo and not item.enlace:
            raise ValidationError('La publicación necesita archivo o enlace de consulta.')
        indicadores = [_indicador(i, unidad) for i in item.indicadores.order_by('pk')]
        if not indicadores or not item.resumen.strip() or not item.periodo.strip():
            raise ValidationError('La publicación debe identificar período, resumen y sus indicadores con metodología.')
        return dict(subtipo=subtipo, id=item.pk,
                    publicacion=_valores(item, ('titulo', 'periodo', 'resumen', 'tipo', 'fecha_publicada', 'enlace')),
                    archivo_sha256=_archivo(item.archivo), indicadores=indicadores)
    if subtipo == 'datos':
        from apps.observatorios.operacion.models.observatorios import IndicadorObservatorio
        item = IndicadorObservatorio.objects.filter(pk=detalle['indicador_id'], unidad=unidad).first()
        if item is None:
            raise ValidationError('Selecciona una serie de este observatorio.')
        indicador = _indicador(item, unidad)
        valores = list(item.valores.filter(pk__in=detalle['valores_ids']).order_by('pk'))
        if len(valores) != len(detalle['valores_ids']) or any(v.provisional for v in valores):
            raise ValidationError('Selecciona datos definitivos pertenecientes a esta serie.')
        for valor in valores:
            _fecha_real(timezone.localdate(valor.registrado), fecha)
            _fecha_real(valor.fecha, fecha)
            if not valor.territorio.strip() or not valor.periodo.strip() or not valor.nota.strip():
                raise ValidationError('Cada dato debe identificar período, territorio y fuente específica.')
        return dict(subtipo=subtipo, id=item.pk, indicador=indicador,
                    valores=[dict(id=v.pk, **_valores(v, ('periodo', 'fecha', 'territorio', 'valor', 'nota', 'origen', 'provisional')))
                             for v in valores])
    if subtipo == 'ensayo':
        from apps.centros_experimentales.operacion.models.centros import CicloProductivo
        item = CicloProductivo.objects.filter(pk=detalle['ciclo_id'], eje__unidad=unidad).select_related('lugar').first()
        if item is None or item.estado not in ('en_curso', 'cerrado') or not item.lugar_id:
            raise ValidationError('El ensayo necesita un ciclo activo o cerrado y una parcela o área identificada.')
        _fecha_real(item.inicio, fecha)
        if item.lugar.unidad_id != unidad.pk:
            raise ValidationError('La parcela o área del ensayo debe pertenecer al centro.')
        registros = list(item.registros.filter(pk__in=detalle['registros_ids']).order_by('fecha', 'pk'))
        if len(registros) != len(detalle['registros_ids']):
            raise ValidationError('El seguimiento debe pertenecer al ciclo seleccionado.')
        for registro in registros:
            _fecha_real(registro.fecha, fecha)
            if registro.fecha < item.inicio:
                raise ValidationError('El seguimiento no puede ser anterior al inicio del ciclo.')
            if not registro.registrado_por_id or not registro.detalle.strip():
                raise ValidationError('El seguimiento necesita fecha, responsable y observación o resultado.')
            if registro.cantidad is not None and registro.cantidad <= 0:
                raise ValidationError('Una medición de seguimiento debe tener cantidad positiva.')
        return dict(subtipo=subtipo, id=item.pk,
                    ciclo=_valores(item, ('nombre', 'tipo', 'rubro', 'lugar_id', 'inicio', 'fin_previsto',
                                         'superficie_ha', 'animales', 'meta', 'unidad_medida')),
                    registros=[dict(id=r.pk, **_valores(r, ('fecha', 'tipo', 'cantidad', 'unidad_medida', 'detalle', 'registrado_por_id')))
                               for r in registros])
    if subtipo == 'produccion':
        from apps.plantas_piloto.operacion.models.produccion import OrdenProduccion
        item = OrdenProduccion.objects.filter(pk=detalle['orden_id'], unidad=unidad).select_related(
            'receta', 'producto', 'responsable').first()
        if (item is None or item.estado != 'terminada' or item.demostrativa or not item.cerrada_en or
                not item.responsable_id or not item.cantidad_obtenida or item.cantidad_obtenida <= 0):
            raise ValidationError('La orden debe estar terminada con responsable, cierre y producto real obtenido.')
        if (item.receta.unidad_id != unidad.pk or item.producto.unidad_id != unidad.pk or
                item.responsable.unidad_id != unidad.pk):
            raise ValidationError('El proceso, producto y responsable de la orden deben pertenecer a esta planta.')
        _fecha_real(timezone.localdate(item.cerrada_en), fecha)
        lotes = list(item.lotes.select_related('producto').order_by('pk'))
        if not lotes or any(lote.demostrativo or lote.cantidad_inicial <= 0 or
                lote.unidad_id != unidad.pk or lote.producto.unidad_id != unidad.pk for lote in lotes):
            raise ValidationError('La orden requiere lotes reales, con cantidad positiva y trazabilidad.')
        for lote in lotes:
            _fecha_real(lote.fecha_produccion, fecha)
        return dict(subtipo=subtipo, id=item.pk,
                    orden=_valores(item, ('codigo', 'producto_id', 'receta_id', 'origen', 'fecha_inicio',
                                         'fecha_fin', 'cantidad_planificada', 'cantidad_obtenida', 'responsable_id', 'cerrada_en', 'detalle_cierre')),
                    lotes=[dict(id=lote.pk, **_valores(lote, ('codigo', 'producto_id', 'cantidad_inicial', 'fecha_produccion')))
                           for lote in lotes])
    from apps.plantas_piloto.operacion.models.calidad import ControlCalidad
    item = ControlCalidad.objects.filter(pk=detalle['control_id'], unidad=unidad).select_related(
        'plan', 'lote_producto', 'lote_consumible__consumible', 'orden').first()
    if (item is None or item.plan.unidad_id != unidad.pk or not item.registrado_por_id or
            not (item.lote_producto_id or item.lote_consumible_id or item.orden_id)):
        raise ValidationError('El control requiere plan, responsable y lote de producto u orden de esta planta.')
    _fecha_real(timezone.localdate(item.fecha), fecha)
    if item.lote_producto_id and (item.lote_producto.unidad_id != unidad.pk or item.lote_producto.demostrativo):
        raise ValidationError('El lote de producto debe ser real y pertenecer a esta planta.')
    if item.lote_producto_id and timezone.localdate(item.fecha) < item.lote_producto.fecha_produccion:
        raise ValidationError('El control de calidad no puede ser anterior a la producción del lote.')
    if item.orden_id and (item.orden.unidad_id != unidad.pk or item.orden.demostrativa):
        raise ValidationError('La orden controlada debe ser real y pertenecer a esta planta.')
    if item.lote_consumible_id and item.lote_consumible.consumible.unidad_id != unidad.pk:
        raise ValidationError('La materia prima controlada debe pertenecer a esta planta.')
    if item.lote_producto_id and item.orden_id and item.lote_producto.orden_id != item.orden_id:
        raise ValidationError('El lote controlado no pertenece a la orden indicada.')
    producto_id = item.lote_producto.producto_id if item.lote_producto_id else item.orden.producto_id if item.orden_id else None
    if item.plan.producto_id and item.plan.producto_id != producto_id:
        raise ValidationError('El plan de calidad no corresponde al producto controlado.')
    if item.plan.consumible_id and (not item.lote_consumible_id or
            item.plan.consumible_id != item.lote_consumible.consumible_id):
        raise ValidationError('El plan de recepción no corresponde a la materia prima controlada.')
    parametros = list(item.plan.parametros.filter(activo=True).order_by('pk'))
    mediciones = list(item.mediciones.select_related('parametro').order_by('parametro_id'))
    if not parametros or {p.pk for p in parametros} != {m.parametro_id for m in mediciones} or len(parametros) != len(mediciones):
        raise ValidationError('El control debe contener una medición de cada parámetro vigente, sin duplicados.')
    for medicion in mediciones:
        parametro = medicion.parametro
        if not parametro.metodo.strip() or (parametro.tipo == 'numerico' and parametro.minimo is None and parametro.maximo is None):
            raise ValidationError('Cada parámetro necesita método y límites de aceptación definidos.')
        if parametro.tipo == 'cualitativo' and not parametro.valor_esperado.strip():
            raise ValidationError('El parámetro cualitativo necesita un valor esperado explícito.')
        if medicion.conforme is not parametro.evaluar(medicion.valor_numerico, medicion.valor_texto):
            raise ValidationError('La conformidad registrada no coincide con la medición y los límites del plan.')
    conforme = all(m.conforme for m in mediciones)
    if item.resultado != ('conforme' if conforme else 'no_conforme'):
        raise ValidationError('El resultado global del control no coincide con sus mediciones.')
    return dict(subtipo=subtipo, id=item.pk, lote=item.lote_producto_id, orden=item.orden_id,
                lote_consumible=item.lote_consumible_id, momento=item.plan.momento,
                control=_valores(item, ('plan_id', 'fecha', 'registrado_por_id', 'resultado', 'observaciones')),
                parametros=[dict(id=p.pk, **_valores(p, ('nombre', 'tipo', 'unidad_medida', 'minimo', 'maximo', 'valor_esperado', 'metodo', 'critico')))
                            for p in parametros],
                mediciones=[dict(parametro=m.parametro_id, valor=m.valor_numerico, texto=m.valor_texto, conforme=m.conforme) for m in mediciones])


def es_revisor_tecnico(unidad, usuario):
    from apps.gestion_unidades.models.espacios import ResponsableUnidad
    return bool(usuario and usuario.is_active and (unidad.administrador_id == usuario.pk or
        ResponsableUnidad.objects.filter(unidad=unidad, usuario=usuario, activo=True,
                                          rol__in=('coordinacion', 'responsable_tecnico')).exists()))


def preparar_verificacion(unidad, usuario, tipo, detalle, fecha):
    if not es_revisor_tecnico(unidad, usuario):
        raise ValidationError('La comprobación corresponde a la coordinación o al responsable técnico de esta unidad.')
    datos = dict(detalle or {})
    datos.pop('fuente_nativa_sha256', None)
    fuente = fotografia_nativa(unidad, tipo, datos, fecha)
    datos['fuente_nativa_sha256'] = huella_nativa(fuente)
    return datos


def verificacion_vigente(unidad, evidencia, original, *, inicio=None, fin=None):
    if (original.get('estado') != 'validado' or original.get('demostracion') is not evidencia.demostracion or
            original.get('_actor_auditoria') != evidencia.validado_por_id or
            original.get('validado_por') != evidencia.validado_por_id or
            original.get('validado_en') != (evidencia.validado_en.isoformat() if evidencia.validado_en else None) or
            not es_revisor_tecnico(unidad, evidencia.validado_por)):
        return False
    try:
        fuente = fotografia_nativa(unidad, evidencia.tipo, evidencia.detalle, evidencia.fecha)
        return (evidencia.detalle.get('fuente_nativa_sha256') == huella_nativa(fuente)
            and (inicio is None or _fuente_del_periodo(evidencia, fuente, inicio, fin)))
    except (ValidationError, ValueError, TypeError, KeyError):
        return False


def _fuente_del_periodo(evidencia, fuente, inicio, fin):
    """La fecha del acta no traslada una actividad antigua al semestre actual.

    Los ensayos pueden atravesar varios semestres; lo que se acredita en cada
    uno es su seguimiento. Las series pueden incorporar datos históricos: la
    actualización se fecha por su incorporación efectiva, no por el año del dato.
    """
    subtipo = fuente['subtipo']
    if subtipo == 'publicacion':
        return inicio <= fuente['publicacion']['fecha_publicada'] <= fin
    if subtipo == 'socializacion':
        return inicio <= date.fromisoformat(fuente['fecha']) <= fin
    if subtipo == 'produccion':
        return inicio <= timezone.localdate(fuente['orden']['cerrada_en']) <= fin
    if subtipo == 'control_calidad':
        return inicio <= timezone.localdate(fuente['control']['fecha']) <= fin
    if subtipo == 'ensayo':
        return any(inicio <= r['fecha'] <= fin for r in fuente['registros'])
    if subtipo == 'datos':
        from apps.observatorios.operacion.models.observatorios import ValorIndicador
        return ValorIndicador.objects.filter(pk__in=evidencia.detalle['valores_ids'],
            registrado__date__range=(inicio, min(fin, evidencia.fecha))).exists()
    return subtipo == 'sin_produccion' and fuente['desde'] == inicio and fuente['hasta'] == fin


def medir_perfiles(unidad, inicio, fin, evidencias):
    """Solo recibe evidencias con auditoría, archivo y captura nativa ya comprobados."""
    from django.conf import settings
    salida = {c: 0 for c in ('gestion_boletines', 'gestion_datos_actualizados', 'gestion_eventos',
                            'gestion_produccion', 'gestion_control_calidad', 'gestion_ensayos')}
    fuentes, vistos = {codigo: [] for codigo in ACTIVIDADES_PERFIL.values()}, set()
    for e in sorted(evidencias, key=lambda e: (e.fecha, e.pk)):
        if (e.tipo not in TIPOS_PERFIL or e.demostracion or getattr(settings, 'MEDICION_SOLO_DEMO', False)):
            continue
        detalle = e.detalle
        subtipo = detalle.get('subtipo')
        if subtipo not in ACTIVIDADES_PERFIL:
            continue
        try:
            nativa = fotografia_nativa(unidad, e.tipo, detalle, e.fecha)
        except (ValidationError, TypeError, ValueError, KeyError):
            continue
        if subtipo == 'ensayo' and not any(inicio <= r['fecha'] <= fin for r in nativa['registros']):
            continue
        if subtipo == 'datos':
            from apps.observatorios.operacion.models.observatorios import ValorIndicador
            if not ValorIndicador.objects.filter(pk__in=detalle['valores_ids'],
                    registrado__date__range=(inicio, min(fin, e.fecha))).exists():
                continue
        identidad = (subtipo, nativa.get('id'),
                     tuple(sorted(detalle.get('valores_ids', []))) if subtipo == 'datos' else
                     () if subtipo == 'ensayo' else
                     (detalle.get('periodo_desde'), detalle.get('periodo_hasta')) if subtipo == 'sin_produccion' else
                     (detalle.get('fecha_evento'), detalle.get('referencia_acta')) if subtipo == 'socializacion' else ())
        if identidad in vistos:
            continue
        # Una actualización vuelve a contar al incorporar datos nuevos, no al volver a guardar la misma serie.
        if subtipo == 'datos':
            datos_vistos = {i for s, id_, ids in vistos if s == 'datos' and id_ == nativa['id'] for i in ids}
            if not set(detalle['valores_ids']) - datos_vistos:
                continue
            if any(f['fecha'] == e.fecha.isoformat() and f['origen']['id'] == nativa['id']
                   for f in fuentes.get('DATOS-ACTUALIZADOS', [])):
                continue
        vistos.add(identidad)
        actividad = ACTIVIDADES_PERFIL[subtipo]
        fuentes.setdefault(actividad, []).append(dict(evidencia=e.pk, codigo=e.codigo,
            fecha=e.fecha.isoformat(), recurso=e.recurso_id, enlace=e.enlace,
            sha256=e.recurso.hash_sha256 if e.recurso_id else '',
            es_pdf=bool(e.recurso_id and Path(e.recurso.archivo.name).suffix.lower() == '.pdf'),
            fuente_nativa_sha256=detalle.get('fuente_nativa_sha256'), origen=nativa))
        campo = {'publicacion': 'gestion_boletines', 'datos': 'gestion_datos_actualizados',
                 'socializacion': 'gestion_eventos', 'produccion': 'gestion_produccion',
                 'control_calidad': 'gestion_control_calidad', 'ensayo': 'gestion_ensayos'}.get(subtipo)
        if campo:
            salida[campo] += 1
    salida['fuentes_perfil'] = fuentes
    if base_perfil(unidad) == 'plantas_piloto':
        from apps.plantas_piloto.operacion.models.produccion import OrdenProduccion, LoteProducto
        corte = min(fin, timezone.localdate())
        ordenes = OrdenProduccion.objects.filter(unidad=unidad, demostrativa=False, estado='terminada',
            cerrada_en__date__range=(inicio, corte)).prefetch_related('lotes')
        universo = {'lote:' + str(pk) for pk in LoteProducto.objects.filter(unidad=unidad,
            demostrativo=False, fecha_produccion__range=(inicio, corte)).values_list('pk', flat=True)}
        por_orden = {}
        for orden in ordenes:
            lotes = list(orden.lotes.filter(demostrativo=False))
            claves = {'lote:' + str(lote.pk) for lote in lotes} or {'orden:' + str(orden.pk)}
            universo.update(claves)
            por_orden[orden.pk] = claves
        cubiertos = set()
        for fuente in fuentes.get('CONTROL-CALIDAD', []):
            origen = fuente['origen']
            if origen.get('momento') != 'liberacion':
                continue
            if origen.get('lote'):
                cubiertos.add('lote:' + str(origen['lote']))
            elif origen.get('orden') in por_orden:
                cubiertos.update(por_orden[origen['orden']])
        justificaciones = [f for f in fuentes.get('CONTROL-CALIDAD', [])
            if f['origen'].get('subtipo') == 'sin_produccion' and
               f['origen']['desde'] == inicio and f['origen']['hasta'] == corte]
        no_aplica = not universo and bool(justificaciones)
        salida['cobertura_calidad'] = dict(numerador=len(cubiertos & universo), denominador=len(universo),
            pendiente=not universo and not no_aplica, no_aplica_verificado=no_aplica,
            motivo='La ausencia de producción finalizada en todo el tramo está justificada y verificada.' if no_aplica else
                '' if universo else 'No hay lotes u órdenes finalizadas verificables; no se presume cumplimiento.',
            fuentes=fuentes.get('CONTROL-CALIDAD', []), universo=sorted(universo))
    return salida
