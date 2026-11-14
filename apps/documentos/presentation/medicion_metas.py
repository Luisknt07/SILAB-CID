"""Mediciones desde evidencias verificadas; nunca desde una marca de revisión del anexo."""
from collections import defaultdict
from calendar import monthrange
from datetime import date
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Min, Q
from django.utils import timezone

from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.models.respaldo_medicion import (
    corte_efectivo, faltantes_desecho, fotografia_criticidad,
    huella_acta_inventario, validar_respaldo, es_unidad_auditable,
    ESQUEMA_VERIFICACION, fecha_verificacion, huella_verificacion,
    requiere_inspecciones_fisicas,
)
from apps.documentos.models.resultados_gestion import TIPOS_RESULTADO, TIPOS_ESTRUCTURADOS, huella_resultado
from apps.documentos.presentation.expediente_operaciones import operacion_de_unidad, recordar_archivo
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.reservas.models.reservas import Reserva
from apps.reservas.models.seguridad import HabilitacionAcceso, RegistroIngreso
from apps.recursos.models.desechos import RegistroDesecho


def habilitada():
    return getattr(settings, 'MEDICION_METAS_HABILITADA', False)


def registrar_evidencia(unidad, usuario, datos, *, verificar=False, archivo=None):
    with operacion_de_unidad(unidad.pk, usuario):
        datos = dict(datos)
        # La atribución y el estado son resultado de esta operación, no datos
        # que el cliente pueda usar para promover un borrador sin verificarlo.
        for protegido in ('estado', 'validado_por', 'validado_por_id', 'validado_en', 'demostracion'):
            datos.pop(protegido, None)
        from .medicion_perfiles import es_revisor_tecnico
        if verificar and es_unidad_auditable(unidad) and not es_revisor_tecnico(unidad, usuario):
            raise ValidationError('La evidencia debe comprobarla un responsable técnico o la coordinación activa de esta unidad.')
        if datos.get('tipo') == 'INVENTARIO' and es_unidad_auditable(unidad):
            detalle = dict(datos.get('detalle') or {})
            # La captura pertenece al servicio; no aceptar una lista inventada
            # enviada por el navegador para declarar que no existen críticos.
            detalle.pop('equipos_criticidad', None)
            detalle.pop('revision_criticidad_en', None)
            if detalle.get('revision_criticidad') is True:
                detalle['equipos_criticidad'] = fotografia_criticidad(unidad)
                detalle['revision_criticidad_en'] = timezone.localdate().isoformat()
            datos['detalle'] = detalle
        if archivo:
            if Path(archivo.name).suffix.lower() not in ('.pdf', '.png', '.jpg', '.jpeg') or archivo.size > 25 * 1024 * 1024:
                raise ValidationError('Adjunta PDF o imagen de hasta 25 MB.')
            if datos.get('recurso') or datos.get('enlace'):
                raise ValidationError('Usa un solo respaldo: archivo nuevo, archivo existente o enlace.')
            from apps.recursos.models.recursos import Recurso
            recurso = Recurso(unidad=unidad, nombre=datos['titulo'], descripcion=datos['descripcion'],
                              visibilidad='interna', descargar=True, tipo_adjunto='evidencia', subido_por=usuario)
            recurso.archivo.save(archivo.name, archivo, save=False)
            recordar_archivo(recurso.archivo)
            recurso.save()
            datos['recurso'] = recurso
        from .medicion_perfiles import preparar_verificacion, usa_contrato_perfil
        if verificar and usa_contrato_perfil(unidad, datos.get('tipo')):
            datos['detalle'] = preparar_verificacion(unidad, usuario, datos['tipo'],
                                                    datos.get('detalle'), datos.get('fecha') or timezone.localdate())
        evidencia = EvidenciaGestionUnidad(unidad=unidad, creado_por=usuario, **datos)
        evidencia.demostracion = bool(getattr(settings, 'MEDICION_SOLO_DEMO', False) or
            evidencia.recurso_id and evidencia.recurso.nombre.startswith('[DEMO REPORTES]'))
        if verificar:
            evidencia.estado = 'validado'
            evidencia.validado_por = usuario
            evidencia.validado_en = timezone.now()
        evidencia.full_clean()
        if verificar and evidencia.recurso_id and EvidenciaGestionUnidad.objects.filter(
                unidad=unidad, tipo=evidencia.tipo, estado='validado',
                recurso__hash_sha256=evidencia.recurso.hash_sha256).exists():
            raise ValidationError('Este mismo archivo ya acredita esta actividad. No se cuenta dos veces.')
        if evidencia.tipo in ('USO', 'DESECHOS') and verificar:
            solapadas = EvidenciaGestionUnidad.objects.filter(unidad=unidad, tipo=evidencia.tipo,
                estado='validado', desde__lte=evidencia.hasta, hasta__gte=evidencia.desde)
            if solapadas.exists():
                raise ValidationError('Ya hay una conciliación verificada para parte de ese tramo. Rectifícala antes de reemplazarla.')
        evidencia.save()
        registrar_auditoria(unidad=unidad, usuario=usuario, accion='crear', objeto=evidencia,
            descripcion=f'Evidencia de medición: {evidencia.codigo}',
            nuevos=dict(tipo=evidencia.tipo, estado=evidencia.estado, demostracion=evidencia.demostracion,
                sha256=evidencia.recurso.hash_sha256 if evidencia.recurso_id else '', enlace=evidencia.enlace,
                detalle=evidencia.detalle,
                **({'alcance_sha256': huella_acta_inventario(evidencia)}
                   if evidencia.tipo == 'INVENTARIO' and es_unidad_auditable(unidad) else {}),
                **({'esquema_verificacion': ESQUEMA_VERIFICACION,
                    'verificacion_sha256': huella_verificacion(evidencia),
                    'validado_por': evidencia.validado_por_id,
                    'validado_en': fecha_verificacion(evidencia.validado_en)}
                   if es_unidad_auditable(unidad) else {}),
                contenido_sha256=huella_resultado(evidencia) if evidencia.tipo in TIPOS_ESTRUCTURADOS else ''))
        return evidencia


def rectificar_evidencia(unidad, usuario, pk, motivo):
    if not str(motivo or '').strip():
        raise ValidationError('Indica el motivo de la rectificación.')
    with operacion_de_unidad(unidad.pk, usuario):
        evidencia = EvidenciaGestionUnidad.objects.select_for_update().get(pk=pk, unidad=unidad)
        if evidencia.estado == 'anulado':
            raise ValidationError('Esta evidencia ya fue rectificada.')
        anterior = evidencia.estado
        evidencia.estado = 'anulado'
        evidencia.save(update_fields=['estado'])
        registrar_auditoria(unidad=unidad, usuario=usuario, accion='actualizar', objeto=evidencia,
            descripcion='Rectificación de evidencia: ' + motivo.strip()[:800],
            anteriores=dict(estado=anterior), nuevos=dict(estado='anulado'))


def medir_seguridad(unidad, inicio, fin):
    """Primera entrada efectiva en la unidad; inducción vigente en esa fecha, sin duplicar personas."""
    if es_unidad_auditable(unidad) and unidad.fecha_inicio:
        inicio = max(inicio, unidad.fecha_inicio)
    fin = corte_efectivo(unidad, fin)
    ingresos = RegistroIngreso.objects.filter(reserva__laboratorio=unidad, ingresa=True,
                                              reserva__fecha__lte=fin)
    desconocidos = ingresos.filter(usuario__isnull=True, reserva__fecha__gte=inicio).exists()
    primeras = ingresos.exclude(usuario__isnull=True).values('usuario_id').annotate(primera=Min('reserva__fecha'))
    nuevos = {r['usuario_id']: r['primera'] for r in primeras if inicio <= r['primera'] <= fin}
    from apps.reservas.models.seguridad import RequisitoAcceso
    requisitos = list(RequisitoAcceso.objects.filter(unidad=unidad, activo=True, tipo='induccion'))
    habilitaciones = list(HabilitacionAcceso.objects.filter(requisito__in=requisitos,
        activa=True, usuario_id__in=nuevos).select_related('requisito'))
    cubiertos = set()
    for usuario, fecha in nuevos.items():
        categorias = set(ingresos.filter(usuario_id=usuario, reserva__fecha=fecha).values_list('categoria', flat=True))
        exigidos = [r for r in requisitos if any(r.aplica(c) for c in categorias)]
        if exigidos and all(any(h.usuario_id == usuario and h.requisito_id == r.pk and
                h.vigente_en(fecha) and (h.documento.strip() or h.reserva_id) for h in habilitaciones)
                for r in exigidos):
            cubiertos.add(usuario)
    return dict(numerador=len(cubiertos), denominador=len(nuevos),
                pendiente=desconocidos,
                motivo='Hay ingresos sin identidad vinculada; no se puede comprobar su primera inducción.' if desconocidos else '')


def _documentar_cero_usuarios_nuevos(unidad, inicio, fin, seguridad, uso):
    """Una lista de ingresos vacía no prueba ausencia de usuarios nuevos.

    Exige conciliación de todas las sesiones y, cuando hubo actividad, identidades
    que concuerden con la asistencia declarada. No concede crédito por no usar la unidad.
    """
    if (seguridad.get('denominador') or seguridad.get('pendiente') or uso.get('pendiente')
            or not uso.get('cobertura_verificada') or not uso.get('fuentes_reales')
            or uso.get('numerador') != uso.get('denominador') or inicio > fin):
        return
    ingresos = list(RegistroIngreso.objects.filter(reserva__laboratorio=unidad, ingresa=True,
        reserva__fecha__range=(inicio, fin)).values_list('reserva_id', 'usuario_id'))
    if any(usuario is None for _, usuario in ingresos):
        return
    por_reserva = defaultdict(set)
    for reserva, usuario in ingresos:
        por_reserva[reserva].add(usuario)
    reservas = [r for r in Reserva.objects.filter(laboratorio=unidad, fecha__range=(inicio, fin)).only(
        'estado', 'resultado_cierre', 'detalle_ejecucion') if r.es_efectiva]
    for reserva in reservas:
        total = reserva.detalle_ejecucion.get('asistentes_total')
        if type(total) is not int or total <= 0 or len(por_reserva.get(reserva.pk, ())) != total:
            return
    if not reservas and ingresos:
        return
    seguridad.update(no_aplica_verificado=True, pendiente=False,
        motivo='La conciliación del tramo y los ingresos identificados verifican que no hubo usuarios nuevos; '
               'se excluye este indicador, sin acreditar actividad ni otorgar 100 %.',
        fuentes=uso.get('fuentes', []), desde=inicio.isoformat(), hasta=fin.isoformat())


def evidencias_verificadas(unidad, evidencias, inicio, fin):
    """Una única regla para metas e informes; conserva los ejemplos identificados como DEMO."""
    evidencias = [e for e in evidencias if e.estado == 'validado']
    from apps.formacion.models.practicas import RegistroAuditoriaUnidad
    auditorias = RegistroAuditoriaUnidad.objects.filter(unidad=unidad, entidad=EvidenciaGestionUnidad._meta.label,
        objeto_id__in=[str(e.pk) for e in evidencias], accion='crear').order_by('pk')
    originales = {a.objeto_id: dict(a.datos_nuevos, _actor_auditoria=a.usuario_id) for a in auditorias}
    # No se acredita una fila incompleta introducida por importación o SQL directo.
    validas = []
    fuentes_vistas = set()
    for e in evidencias:
        try:
            e.full_clean(validate_unique=False, validate_constraints=False)
        except ValidationError:
            continue
        if e.tipo in ('USO', 'DESECHOS') and (e.desde < inicio or e.hasta > fin):
            continue
        original = originales.get(str(e.pk), {})
        if es_unidad_auditable(unidad):
            from .medicion_perfiles import es_revisor_tecnico
            if (original.get('estado') != 'validado' or original.get('demostracion') is not e.demostracion or
                    original.get('_actor_auditoria') != e.validado_por_id or
                    original.get('validado_por') != e.validado_por_id or
                    original.get('validado_en') != fecha_verificacion(e.validado_en) or
                    original.get('esquema_verificacion') != ESQUEMA_VERIFICACION or
                    original.get('verificacion_sha256') != huella_verificacion(e) or
                    not es_revisor_tecnico(unidad, e.validado_por)):
                continue
        if e.recurso_id and original.get('sha256') != e.recurso.hash_sha256:
            continue
        if not e.recurso_id and original.get('enlace') != e.enlace:
            continue
        if e.tipo in TIPOS_ESTRUCTURADOS and original.get('contenido_sha256') != huella_resultado(e):
            continue
        from .medicion_perfiles import usa_contrato_perfil, verificacion_vigente
        if usa_contrato_perfil(unidad, e.tipo) and not verificacion_vigente(
                unidad, e, original, inicio=inicio, fin=fin):
            continue
        if e.tipo == 'INVENTARIO' and es_unidad_auditable(unidad) and original.get('alcance_sha256') != huella_acta_inventario(e):
            continue
        identidad = (e.tipo, e.recurso.hash_sha256 if e.recurso_id else e.enlace)
        if identidad in fuentes_vistas:
            continue
        fuentes_vistas.add(identidad)
        validas.append(e)
    return validas


def resultados_documentados(unidad, inicio, fin, tipo):
    """Resultados con su producto y soporte; no convierte reservas en resultados de investigación.

    Las filas conservan borradores, rectificaciones y ejemplos visibles con su estado.
    Solo las verificadas con huella vigente y fuera de DEMO acreditan un resultado real.
    """
    if tipo not in TIPOS_RESULTADO:
        raise ValueError('Tipo de resultado no admitido.')
    return _documentadas_estructuradas(unidad, inicio, fin, tipo)


def inspecciones_documentadas(unidad, inicio, fin):
    """Chequeos y acciones con su estado documental; nunca habilitan por sí mismos la operación."""
    return _documentadas_estructuradas(unidad, inicio, fin, 'INSPECCION')


def _documentadas_estructuradas(unidad, inicio, fin, tipo):
    fin = corte_efectivo(unidad, fin)
    evidencias = list(EvidenciaGestionUnidad.objects.filter(unidad=unidad, tipo=tipo,
        fecha__range=(inicio, fin)).select_related('recurso', 'responsable'))
    validas = evidencias_verificadas(unidad, evidencias, inicio, fin) if habilitada() else []
    verificadas = {e.pk for e in validas}
    demo_global = getattr(settings, 'MEDICION_SOLO_DEMO', False)
    filas = []
    for e in evidencias:
        detalle = e.detalle if isinstance(e.detalle, dict) else {}
        demo = bool(e.demostracion or demo_global)
        verificada = e.pk in verificadas
        filas.append(dict(pk=e.pk, codigo=e.codigo, fecha=e.fecha, titulo=e.titulo,
            resultado=e.descripcion, responsable=str(e.responsable),
            proyecto=detalle.get('proyecto', ''), tipo_producto=detalle.get('tipo_producto', ''),
            producto=detalle.get('producto', ''), beneficiario=detalle.get('beneficiario', ''),
            aceptacion=detalle.get('aceptacion', ''), fecha_aceptacion=detalle.get('fecha_aceptacion', ''),
            referencia_aceptacion=detalle.get('referencia_aceptacion', ''), estado=e.estado,
            area=detalle.get('area', ''), condiciones_revisadas=detalle.get('condiciones_revisadas', []),
            sin_hallazgos=detalle.get('sin_hallazgos', False), hallazgos=detalle.get('hallazgos', ''),
            accion_correctiva=detalle.get('accion_correctiva', ''),
            estado_condiciones=detalle.get('estado_condiciones', ''),
            estado_accion=detalle.get('estado_accion', ''), plazo_accion=detalle.get('plazo_accion', ''),
            estado_display=('Rectificado' if e.estado == 'anulado' else
                'Verificado · DEMO' if verificada and demo else 'Verificado' if verificada else
                'Verificación pendiente' if e.estado == 'validado' else 'Borrador'),
            verificada=verificada, demostracion=demo, acredita=verificada and not demo,
            recurso=e.recurso_id, es_pdf=bool(e.recurso_id and Path(e.recurso.archivo.name).suffix.lower() == '.pdf'),
            sha256=e.recurso.hash_sha256 if e.recurso_id else '', enlace=e.enlace,
            detalle=detalle))
    return dict(filas=filas, registrados=len(filas), verificados=len(validas),
                reales=sum(f['acredita'] for f in filas),
                demostracion=sum(f['verificada'] and f['demostracion'] for f in filas),
                pendientes=sum(not f['verificada'] and f['estado'] != 'anulado' for f in filas))


def cobertura_mensual_inspecciones(unidad, inicio, fin):
    """Una revisión verificada en octubre no cubre agosto ni septiembre.

    El mes en curso se identifica como pendiente dentro de plazo. La cobertura
    describe revisiones documentadas y su alcance, no un permiso para operar.
    """
    if not requiere_inspecciones_fisicas(unidad):
        return None
    if unidad.fecha_inicio:
        inicio = max(inicio, unidad.fecha_inicio)
    corte = corte_efectivo(unidad, fin)
    documentadas = inspecciones_documentadas(unidad, inicio, corte)['filas'] if inicio <= corte else []
    por_mes = defaultdict(list)
    for fila in documentadas:
        if fila['estado'] != 'anulado':
            por_mes[(fila['fecha'].year, fila['fecha'].month)].append(fila)
    filas = []
    mes = inicio.replace(day=1)
    while mes <= corte:
        fin_mes = date(mes.year, mes.month, monthrange(mes.year, mes.month)[1])
        revisiones = por_mes[(mes.year, mes.month)]
        reales = [f for f in revisiones if f['acredita']]
        demos = [f for f in revisiones if f['demostracion']]
        vigente = min(fin_mes, fin) >= timezone.localdate()
        exigible = min(fin_mes, fin) <= corte
        filas.append(dict(mes=f'{mes.year}-{mes.month:02d}', desde=max(mes, inicio).isoformat(),
            hasta=min(fin_mes, fin).isoformat(), corte=corte.isoformat(),
            revisiones=len(revisiones), verificadas_reales=len(reales), demostracion=len(demos),
            cumple=bool(reales), dentro_plazo=vigente, exigible=exigible,
            estado='Revisión documentada' if reales else 'Pendiente: mes en curso' if vigente else
                   'Sin revisión verificada del mes',
            codigos=[f['codigo'] for f in reales],
            fuentes=[dict(evidencia=f['pk'], codigo=f['codigo'], mes=f'{mes.year}-{mes.month:02d}',
                          recurso=f['recurso'], es_pdf=f['es_pdf'], sha256=f['sha256'], enlace=f['enlace'])
                     for f in reales],
            areas=sorted({f['area'] for f in reales if f['area']})))
        mes = date(mes.year + 1, 1, 1) if mes.month == 12 else date(mes.year, mes.month + 1, 1)
    return dict(corte=corte.isoformat(), meses=filas, exigidos=len(filas),
                cubiertos=sum(f['cumple'] for f in filas),
                exigibles=sum(f['exigible'] for f in filas),
                cubiertos_exigibles=sum(f['cumple'] and f['exigible'] for f in filas),
                vencidos_sin_revision=sum(not f['cumple'] and not f['dentro_plazo'] for f in filas),
                pendientes_en_plazo=sum(not f['cumple'] and f['dentro_plazo'] for f in filas))


def _revision_criticidad_documentada(unidad, inicio, corte):
    """Una lista vacía sólo es conocida si fue revisada con acta y archivo real."""
    if not habilitada():
        return []
    actas = list(EvidenciaGestionUnidad.objects.filter(unidad=unidad, tipo='INVENTARIO',
        fecha__range=(inicio, corte), estado='validado', demostracion=False).select_related('recurso'))
    actuales = fotografia_criticidad(unidad)
    fuentes = []
    for acta in evidencias_verificadas(unidad, actas, inicio, corte):
        detalle = acta.detalle if isinstance(acta.detalle, dict) else {}
        if (getattr(settings, 'MEDICION_SOLO_DEMO', False) or not acta.recurso_id or
                detalle.get('revision_criticidad') is not True or
                detalle.get('equipos_criticidad') != actuales):
            continue
        try:
            revisada = date.fromisoformat(detalle.get('revision_criticidad_en', ''))
        except (ValueError, TypeError):
            continue
        if not inicio <= revisada <= corte:
            continue
        fuentes.append(dict(evidencia=acta.pk, codigo=acta.codigo, recurso=acta.recurso_id,
            es_pdf=Path(acta.recurso.archivo.name).suffix.lower() == '.pdf',
            sha256=acta.recurso.hash_sha256, alcance_sha256=huella_acta_inventario(acta),
            revision_criticidad_en=revisada.isoformat(), equipos_criticidad=actuales))
    return fuentes


def medir_mantenimiento_critico(unidad, inicio, fin):
    """Ejecución respaldada del programa anual crítico, separada de todas las órdenes."""
    from apps.documentos.presentation.perfil_unidades import es_unidad_auditable
    if not es_unidad_auditable(unidad):
        return None
    from apps.recursos.models.unidades import UnidadEquipo
    from apps.recursos.models.mantenimiento import MantenimientoEquipo, PlanMantenimientoEquipo
    corte = corte_efectivo(unidad, fin)
    inicio_anual, fin_anual = date(inicio.year, 1, 1), date(inicio.year, 12, 31)
    equipos = UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad),
        activa=True, fecha_baja__isnull=True, criticidad='critico').distinct()
    claves = list(equipos.values_list('pk', flat=True))
    from apps.gestion_unidades.models.espacios import ResponsableUnidad
    responsables = set(ResponsableUnidad.objects.filter(unidad=unidad, activo=True,
        usuario__is_active=True).values_list('usuario_id', flat=True))
    if unidad.administrador_id and unidad.administrador.is_active:
        responsables.add(unidad.administrador_id)
    planes = list(PlanMantenimientoEquipo.objects.filter(equipo_id__in=claves, activo=True, fecha_inicio__lte=corte))
    ids_con_plan = {p.equipo_id for p in planes}
    planes_respaldados = {p.pk: p for p in planes if p.responsable_id in responsables or p.proveedor.strip()}
    ids_plan_responsable = {p.equipo_id for p in planes_respaldados.values()}
    anuales = MantenimientoEquipo.objects.filter(
        Q(unidad=unidad) | Q(unidad__isnull=True, equipo_id__in=claves),
        equipo_id__in=claves, fecha_programada__date__range=(inicio_anual, fin_anual),
    ).select_related('responsable').order_by('fecha_programada', 'pk')
    ids_programados = set(anuales.values_list('equipo_id', flat=True))
    ordenes = anuales.filter(fecha_programada__date__lte=corte)
    acreditadas, pendientes_respaldo, fuentes_ordenes, no_acreditables = [], [], [], []
    for orden in ordenes:
        if (orden.estado != 'completado' or not orden.fecha_fin or
                timezone.localtime(orden.fecha_fin).date() > corte):
            continue
        faltantes = []
        if orden.responsable_id not in responsables:
            faltantes.append('responsable vinculado a la unidad')
        if orden.unidad_id != unidad.pk:
            faltantes.append('unidad responsable explícita en la orden')
        plan = planes_respaldados.get(orden.plan_id)
        if not plan or plan.equipo_id != orden.equipo_id:
            faltantes.append('plan activo del mismo equipo con responsable o proveedor')
        if not orden.resultado.strip():
            faltantes.append('resultado de la intervención')
        if (not orden.fecha_inicio or orden.fecha_inicio > orden.fecha_fin or
                plan and timezone.localtime(orden.fecha_inicio).date() < plan.fecha_inicio):
            faltantes.append('fechas reales coherentes')
        try:
            if not orden.informe:
                raise ValidationError('Falta respaldo de la ejecución.')
            huella = validar_respaldo(orden.informe)
        except ValidationError:
            faltantes.append('informe legible y disponible')
        if faltantes:
            pendientes_respaldo.append(orden.codigo)
            no_acreditables.append(dict(codigo=orden.codigo, faltantes=faltantes))
        else:
            if not getattr(settings, 'MEDICION_SOLO_DEMO', False):
                acreditadas.append(orden.codigo)
                fuentes_ordenes.append(dict(orden=orden.pk, codigo=orden.codigo, tipo='MANTENIMIENTO-EQUIPO',
                    equipo=orden.equipo_id, responsable=orden.responsable_id, plan=orden.plan_id,
                    fecha_programada=orden.fecha_programada.isoformat(), fecha_inicio=orden.fecha_inicio.isoformat(),
                    fecha_fin=orden.fecha_fin.isoformat(), resultado=orden.resultado,
                    archivo=orden.informe.name, sha256=huella))
    faltan_planes = len(set(claves) - ids_con_plan)
    faltan_responsables = len(set(claves) - ids_plan_responsable)
    falta_programacion = len(set(claves) - ids_programados)
    motivos = []
    revision = _revision_criticidad_documentada(unidad, inicio_anual, corte)
    universo_conocido = bool(revision)
    no_aplica = bool(not claves and revision)
    if not universo_conocido:
        motivos.append('Falta un acta vigente con archivo y revisión de criticidad de todos los equipos; '
                       'los críticos identificados se muestran provisionalmente.')
    if faltan_planes:
        motivos.append(f'{faltan_planes} equipos críticos sin plan activo.')
    if faltan_responsables:
        motivos.append(f'{faltan_responsables} equipos críticos sin responsable o proveedor en su plan.')
    if falta_programacion:
        motivos.append(f'{falta_programacion} equipos críticos sin órdenes en el programa anual.')
    futuras = anuales.filter(fecha_programada__date__gt=corte).count()
    if claves and not ordenes:
        motivos.append('No hay intervenciones críticas exigibles al corte; la programación futura sigue dentro de plazo.'
                       if futuras else 'Falta programación verificable del mantenimiento anual crítico.')
    return dict(numerador=len(acreditadas), denominador=len(ordenes), pendiente=bool(motivos),
        motivo=' '.join(motivos), corte=corte.isoformat(), desde=inicio_anual.isoformat(), hasta=fin_anual.isoformat(),
        equipos_criticos=len(claves), equipos_sin_plan=faltan_planes,
        equipos_sin_responsable=faltan_responsables, equipos_sin_programacion=falta_programacion,
        completadas_sin_respaldo=pendientes_respaldo, ordenes_acreditadas=acreditadas,
        ordenes_no_acreditables=no_acreditables,
        universo_conocido=universo_conocido, no_aplica_verificado=no_aplica, fuentes=revision + fuentes_ordenes,
        programadas_anuales=anuales.count(), programadas_futuras=futuras,
        alcance='Programa anual de equipos críticos; las inspecciones de infraestructura no sustituyen su plan de mantenimiento.')


def medir_mantenimiento_integral(unidad, inicio, fin):
    """Programa crítico anual de equipos e infraestructura, exigible sólo al corte.

    Conserva ambas submediciones para explicar su respaldo. Una declaración
    revisada de ausencia de intervenciones críticas se trata como no aplicable,
    nunca como una ejecución del cien por ciento sobre cero órdenes.
    """
    from apps.documentos.presentation.perfil_unidades import es_unidad_auditable
    if not es_unidad_auditable(unidad):
        return None
    from apps.documentos.presentation.infraestructura_laboratorios import infraestructura_documentada
    equipos = medir_mantenimiento_critico(unidad, inicio, fin)
    anual_inicio, anual_fin = date(inicio.year, 1, 1), date(inicio.year, 12, 31)
    infra = infraestructura_documentada(unidad, anual_inicio, anual_fin)
    criticas = [f for f in infra['ocurrencias'] if f['criticidad'] == 'critica' and not f['demostracion']]
    futuras = [f for f in infra['futuras'] if f['criticidad'] == 'critica' and not f['demostracion']]
    exigibles = [f for f in criticas if f['plan_verificado']]
    futuras_reales = [f for f in futuras if f['plan_verificado']]
    fuentes = list(equipos['fuentes'])
    fuentes.extend(dict(evidencia=f['pk'], codigo=f['codigo'], recurso=f['recurso'], es_pdf=f['es_pdf'],
        sha256=f['sha256'], contenido_sha256=f['contenido_sha256'], tipo='PLAN-INFRA')
        for f in infra['planes'] if f['acredita'])
    fuentes.extend(dict(evidencia=f['pk'], codigo=f['codigo'], recurso=f['recurso'], es_pdf=f['es_pdf'],
        sha256=f['sha256'], contenido_sha256=f['contenido_sha256'], tipo='EJECUCION-INFRA')
        for f in infra['ejecuciones'] if f['acredita'])
    sin_verificar = any(not f['plan_verificado'] for f in criticas + futuras)
    motivo_infra = ('Hay declaraciones contradictorias del alcance de infraestructura.'
        if infra['alcance_contradictorio'] else
        'Hay espacios de la unidad sin cobertura verificada del plan de infraestructura: ' +
        ', '.join(f'{e["codigo"]} · {e["nombre"]}' for e in infra['espacios_sin_cobertura']) + '.'
        if infra['espacios_sin_cobertura'] else
        'Falta un plan de infraestructura verificado o una declaración respaldada de no aplicación.'
        if not infra['alcance_declarado'] else
        'Hay intervenciones críticas cuyo plan de infraestructura no está verificado.'
        if sin_verificar else
        'La programación crítica de infraestructura aún está dentro de plazo.'
        if futuras_reales and not exigibles else '')
    infraestructura = dict(numerador=sum(f['acredita'] for f in exigibles), denominador=len(exigibles),
        pendiente=bool(motivo_infra), motivo=motivo_infra, universo_conocido=infra['alcance_declarado'],
        no_aplica_verificado=bool(infra['alcance_declarado'] and not criticas and not futuras),
        programadas_futuras=len(futuras_reales), alcance=infra['fuentes_alcance'],
        espacios_sin_cobertura=infra['espacios_sin_cobertura'],
        espacios_del_laboratorio=infra['espacios_del_laboratorio'],
        espacios_de_la_unidad=infra['espacios_del_laboratorio'],
        cobertura_global_declarada=infra['cobertura_global_declarada'],
        corte=infra['corte'], justificacion=infra['justificacion'])
    numerador = equipos['numerador'] + infraestructura['numerador']
    denominador = equipos['denominador'] + infraestructura['denominador']
    no_aplica = bool(equipos['no_aplica_verificado'] and infraestructura['no_aplica_verificado'])
    motivos = [f'Equipos: {equipos["motivo"]}'] if equipos['motivo'] else []
    if motivo_infra:
        motivos.append('Infraestructura: ' + motivo_infra)
    if no_aplica:
        motivos = ['Sin intervenciones críticas exigibles: el universo de equipos fue revisado en un acta '
                   'vigente y el alcance de infraestructura está respaldado. No equivale a ejecutar el 100 % de un plan.']
    return dict(numerador=numerador, denominador=denominador,
        pendiente=bool(motivos) and not no_aplica, no_aplica_verificado=no_aplica,
        motivo=' '.join(motivos), corte=equipos['corte'], desde=equipos['desde'], hasta=equipos['hasta'],
        equipos=equipos, infraestructura=infraestructura, fuentes=fuentes,
        programadas_futuras=equipos['programadas_futuras'] + len(futuras_reales),
        alcance='Intervenciones críticas exigibles del programa anual de equipos e infraestructura; '
                'el calendario futuro se conserva dentro de plazo.')


def registros_de_gestion(unidad, inicio, fin):
    if not habilitada():
        return {}
    if es_unidad_auditable(unidad) and unidad.fecha_inicio:
        inicio = max(inicio, unidad.fecha_inicio)
    fin_consultado = fin
    fin = corte_efectivo(unidad, fin)
    evidencias = list(EvidenciaGestionUnidad.objects.filter(unidad=unidad, fecha__range=(inicio, fin),
        estado='validado').select_related('recurso'))
    validas = evidencias_verificadas(unidad, evidencias, inicio, fin)
    por_tipo = defaultdict(list)
    for e in validas:
        por_tipo[e.tipo].append(e)
    salida = {'gestion_' + tipo.lower(): len(por_tipo[tipo]) for tipo, _ in EvidenciaGestionUnidad.TIPOS}
    salida['inventarios_verificados'] = len(por_tipo['INVENTARIO'])
    salida['resultados_verificados'] = len(por_tipo['INVESTIGACION'])
    salida['transferencias_verificadas'] = len(por_tipo['TRANSFERENCIA'])
    demo_global = getattr(settings, 'MEDICION_SOLO_DEMO', False)
    salida['resultados_reales'] = sum(not (e.demostracion or demo_global) for e in por_tipo['INVESTIGACION'])
    salida['transferencias_reales'] = sum(not (e.demostracion or demo_global) for e in por_tipo['TRANSFERENCIA'])
    salida['fuentes_gestion'] = {tipo: [dict(evidencia=e.pk, codigo=e.codigo, fecha=e.fecha.isoformat(),
        recurso=e.recurso_id, es_pdf=bool(e.recurso_id and Path(e.recurso.archivo.name).suffix.lower() == '.pdf'),
        sha256=e.recurso.hash_sha256 if e.recurso_id else '',
        enlace=e.enlace, titulo=e.titulo, detalle=e.detalle,
        contenido_sha256=huella_resultado(e) if e.tipo in TIPOS_ESTRUCTURADOS else '',
        **({'alcance_sha256': huella_acta_inventario(e), 'alcance': list(e.alcance)}
           if e.tipo == 'INVENTARIO' and es_unidad_auditable(unidad) else {}),
        demostracion=e.demostracion) for e in filas] for tipo, filas in por_tipo.items()}
    salida['mediciones_porcentuales'] = {'SEGURIDAD': medir_seguridad(unidad, inicio, fin)}
    if requiere_inspecciones_fisicas(unidad):
        salida['cobertura_inspecciones'] = cobertura_mensual_inspecciones(unidad, inicio, fin_consultado)
        mensual = salida['cobertura_inspecciones']
        meses_faltantes = [m['mes'] for m in mensual['meses'] if m['exigible'] and not m['cumple']]
        salida['meses_inspeccion_cubiertos'] = mensual['cubiertos_exigibles']
        salida['mediciones_porcentuales']['INSPECCIONES'] = dict(
            numerador=mensual['cubiertos_exigibles'], denominador=mensual['exigibles'],
            pendiente=not mensual['exigibles'],
            motivo='Aún no hay meses exigibles al corte; el mes en curso es provisional.' if not mensual['exigibles']
                else 'Faltan revisiones verificadas de: ' + ', '.join(meses_faltantes) + '.' if meses_faltantes else '',
            fuentes=[f for m in mensual['meses'] if m['exigible'] for f in m['fuentes']],
            corte=mensual['corte'], cobertura=mensual,
        )
    if es_unidad_auditable(unidad):
        salida['mediciones_porcentuales']['MANTENIMIENTO'] = medir_mantenimiento_integral(unidad, inicio, fin_consultado)
    for tipo in ('USO', 'DESECHOS'):
        actas = sorted(por_tipo[tipo], key=lambda e: e.desde)
        solapadas = any(a.hasta >= b.desde for a, b in zip(actas, actas[1:]))
        numerador = 0
        for acta in actas:
            if tipo == 'USO':
                reservas = Reserva.objects.filter(laboratorio=unidad, fecha__range=(acta.desde, acta.hasta))
                numerador += sum(r.es_efectiva for r in reservas.only('estado', 'resultado_cierre', 'detalle_ejecucion'))
            else:
                desechos = RegistroDesecho.objects.filter(unidad=unidad, fecha_generacion__range=(acta.desde, acta.hasta))
                if es_unidad_auditable(unidad):
                    numerador += sum(not faltantes_desecho(d, validar_archivo=True, al_corte=fin) for d in desechos)
                else:
                    numerador += sum(bool(d.cantidad > 0 and d.envase.strip() and d.etiquetado and
                    d.responsable_id and (d.almacenamiento.strip() or d.etapa == 'entregado') and
                    (d.etapa != 'entregado' or d.manifiesto.strip() and d.gestor_autorizado.strip() and d.fecha_entrega))
                    for d in desechos)
        denominador = sum(a.total_observado or 0 for a in actas)
        hasta_medicion = min(fin, timezone.localdate())
        cobertura = bool(actas and actas[0].desde == inicio and actas[-1].hasta == hasta_medicion and
            all((b.desde - a.hasta).days == 1 for a, b in zip(actas, actas[1:])))
        pendiente = solapadas or numerador > denominador or not cobertura
        fuentes_reales = bool(actas) and not demo_global and not any(a.demostracion for a in actas)
        sin_desechos = bool(tipo == 'DESECHOS' and not pendiente and fuentes_reales and
            denominador == 0 and not RegistroDesecho.objects.filter(
                unidad=unidad, fecha_generacion__range=(inicio, fin)).exists())
        motivo = ('La conciliación contiene tramos solapados o más registros que el total observado.'
                  if solapadas or numerador > denominador else
                  'Falta conciliar todo el período transcurrido hasta la fecha de medición.' if not cobertura else '')
        if sin_desechos:
            motivo = ('La ausencia de generación de desechos está conciliada y verificada en todo el tramo; '
                      'se excluye este indicador, sin otorgar 100 %.')
        salida['mediciones_porcentuales'][tipo] = dict(numerador=numerador, denominador=denominador,
            pendiente=pendiente, motivo=motivo, no_aplica_verificado=sin_desechos,
            cobertura_verificada=cobertura and not solapadas, fuentes_reales=fuentes_reales,
            desde=inicio.isoformat(), hasta=hasta_medicion.isoformat(),
            fuentes=[dict(evidencia=a.pk, codigo=a.codigo, desde=a.desde.isoformat(), hasta=a.hasta.isoformat(),
                          recurso=a.recurso_id, es_pdf=bool(a.recurso_id and Path(a.recurso.archivo.name).suffix.lower() == '.pdf'),
                          sha256=a.recurso.hash_sha256 if a.recurso_id else '',
                          enlace=a.enlace) for a in actas])
    _documentar_cero_usuarios_nuevos(unidad, inicio, fin,
        salida['mediciones_porcentuales']['SEGURIDAD'], salida['mediciones_porcentuales']['USO'])
    salida['evidencias_demo'] = bool(getattr(settings, 'MEDICION_SOLO_DEMO', False) or any(e.demostracion for e in evidencias))
    from .medicion_perfiles import BASES_PERFIL, base_perfil, medir_perfiles
    if base_perfil(unidad) in BASES_PERFIL:
        perfil = medir_perfiles(unidad, inicio, fin, validas)
        salida['fuentes_gestion'].update(perfil.pop('fuentes_perfil'))
        if 'cobertura_calidad' in perfil:
            salida['mediciones_porcentuales']['CONTROL-CALIDAD'] = perfil.pop('cobertura_calidad')
        salida.update(perfil)
    return salida
