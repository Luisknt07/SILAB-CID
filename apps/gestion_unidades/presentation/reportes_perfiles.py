"""Reportes con las fuentes propias de observatorios, plantas piloto y centros experimentales."""
from datetime import datetime

from django.utils import timezone
from django.urls import reverse

from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.medicion_metas import evidencias_verificadas, habilitada
from apps.documentos.presentation.medicion_perfiles import base_perfil, medir_perfiles

CATEGORIAS_PERFIL = ('boletines', 'datos-observatorio', 'eventos', 'ensayos', 'produccion-agropecuaria',
                     'control-calidad')
# Tipo y subtipo de la evidencia de gestión que acredita la revisión técnica de cada categoría.
# La producción agropecuaria es un registro del período: no tiene evidencia de revisión técnica.
CATEGORIA_RESULTADO = {'boletines': ('BOLETINES', 'publicacion'),
    'datos-observatorio': ('BOLETINES', 'datos'), 'eventos': ('EVENTOS', 'socializacion'),
    'ensayos': ('ENSAYOS', 'ensayo'), 'control-calidad': ('PRODUCCION', 'control_calidad'),
    'produccion': ('PRODUCCION', 'produccion'), 'produccion-agropecuaria': ('', '')}
# Registros del centro que mueven producto; los demás son manejo del ciclo.
MOVIMIENTOS_DE_PRODUCCION = ('cosecha', 'ordeno', 'postura', 'salida', 'entrega')


def _texto(valor):
    if isinstance(valor, datetime) and timezone.is_aware(valor):
        valor = timezone.localtime(valor)
    return valor.strftime('%d/%m/%Y') if hasattr(valor, 'strftime') else str(valor if valor not in (None, '') else '—')


def _tabla_perfil(titulo, headers, filas):
    return dict(titulo=titulo, headers=headers, rows=filas[:500], total=len(filas), truncated=len(filas) > 500)


def _persona(usuario):
    return (usuario.get_full_name() or usuario.get_username()) if usuario else 'Sin identificar'


def ciclos_del_periodo(unidad, inicio, fin, *, ensayos):
    """Ciclos del centro vigentes en el período: los ensayos o los productivos, nunca mezclados.

    Un ensayo es investigación y un ciclo productivo es producción. Cada ciclo trae en
    ``registros_del_periodo`` sus registros con fecha dentro del período, por fecha.
    """
    from django.db.models import Prefetch, Q
    from apps.centros_experimentales.operacion.models.centros import CicloProductivo, RegistroProduccion

    registros = (RegistroProduccion.objects.filter(fecha__range=(inicio, fin))
                 .select_related('registrado_por').order_by('fecha', 'pk'))
    return list(CicloProductivo.objects.filter(eje__unidad=unidad, es_ensayo=ensayos, inicio__lte=fin)
                .filter(Q(fin__isnull=True) | Q(fin__gte=inicio))
                .select_related('eje', 'lugar', 'responsable')
                .prefetch_related(Prefetch('registros', queryset=registros, to_attr='registros_del_periodo'))
                .order_by('inicio', 'nombre', 'pk'))


def produccion_de_los_ciclos(ciclos, inicio, corte):
    """{ciclo: (obtenido desde su inicio, obtenido en el período)}, en la unidad de medida de su meta.

    Suma cosechas, ordeños, posturas y salidas hasta el corte, como ``CicloProductivo.producido``.
    """
    from django.db.models import Q, Sum
    from apps.centros_experimentales.operacion.models.centros import RegistroProduccion

    medidas = {c.pk: c.unidad_medida for c in ciclos}
    totales = {pk: [0, 0] for pk in medidas}
    sumas = (RegistroProduccion.objects.filter(ciclo_id__in=medidas, tipo__in=RegistroProduccion.PRODUCCION,
                                               fecha__lte=corte)
             .values('ciclo_id', 'unidad_medida')
             .annotate(total=Sum('cantidad'), periodo=Sum('cantidad', filter=Q(fecha__gte=inicio))))
    for suma in sumas:
        if suma['unidad_medida'] == medidas[suma['ciclo_id']]:
            totales[suma['ciclo_id']] = [suma['total'] or 0, suma['periodo'] or 0]
    return {pk: tuple(sumado) for pk, sumado in totales.items()}


def pendientes_de_trazabilidad(ciclo, registros, corte):
    """Lo que le falta a un ciclo productivo y a sus registros del período para poder seguirlos.

    Comprueba datos, no resultados: no califica el manejo ni el rendimiento del ciclo.
    """
    from apps.centros_experimentales.operacion.models.centros import RegistroProduccion

    faltan = []
    if not ciclo.lugar_id:
        faltan.append('área o lote del centro')
    elif ciclo.lugar.unidad_id != ciclo.eje.unidad_id:
        faltan.append('área que pertenezca al centro')
    if not ciclo.meta or ciclo.meta <= 0:
        faltan.append('meta de producción')
    if ciclo.tipo in ('hato', 'lote') and not ciclo.animales:
        faltan.append('número de animales')
    if ciclo.tipo == 'cultivo' and not ciclo.superficie_ha:
        faltan.append('superficie')
    if ciclo.estado == 'cerrado' and not ciclo.fin:
        faltan.append('fecha de fin real')
    if ciclo.estado == 'en_curso' and ciclo.inicio <= corte and not registros:
        faltan.append('registros en el período')
    con_cantidad = (*RegistroProduccion.PRODUCCION, 'entrega')
    cuentas = {clave: 0 for clave in ('responsable', 'fecha', 'cantidad', 'unidad', 'destino', 'detalle')}
    for r in registros:
        cuentas['responsable'] += not r.registrado_por_id
        cuentas['fecha'] += r.fecha < ciclo.inicio or r.fecha > corte
        if r.tipo in con_cantidad:
            cuentas['cantidad'] += r.cantidad is None or r.cantidad <= 0 or not r.unidad_medida
            cuentas['unidad'] += bool(r.tipo in RegistroProduccion.PRODUCCION and r.unidad_medida
                                      and r.unidad_medida != ciclo.unidad_medida)
            cuentas['destino'] += r.tipo == 'entrega' and not r.destino
        else:
            cuentas['detalle'] += not r.detalle.strip()
    mensajes = {'responsable': 'quién registró', 'fecha': 'fecha dentro del ciclo y hasta el corte',
                'cantidad': 'cantidad y unidad de medida', 'unidad': 'la unidad de medida de la meta',
                'destino': 'destino de la entrega', 'detalle': 'detalle de lo realizado'}
    for clave, cuantos in cuentas.items():
        if cuantos:
            faltan.append(f"{mensajes[clave]} en {cuantos} {'registro' if cuantos == 1 else 'registros'}")
    return faltan


def _tablas_no_conformidades(unidad, inicio, corte, revisados, seleccionados, estado, buscar):
    """Hallazgos reales y sus acciones; el estado se informa, no se presume su cierre."""
    from django.db.models import Q
    from apps.plantas_piloto.operacion.models.calidad import NoConformidad

    consulta = NoConformidad.objects.reales().filter(unidad=unidad, detectada_en__date__lte=corte).filter(
        Q(detectada_en__date__gte=inicio) | Q(cerrada_en__date__gte=inicio) | ~Q(estado='cerrada'))
    consulta = consulta.select_related('lote_producto', 'lote_consumible', 'control').prefetch_related(
        'acciones__responsable')
    hallazgos, acciones, capturas = [], [], []
    for n in consulta:
        revision = bool(n.control_id and n.control_id in revisados)
        if estado == 'validado' and not revision or estado == 'pendiente' and revision:
            continue
        tareas = list(n.acciones.all())
        objeto = n.objeto if n.lote_producto_id or n.lote_consumible_id or not n.control_id else n.control.objeto
        valores = [n.codigo, _texto(n.detectada_en), objeto,
            n.descripcion + (f' Causa: {n.causa}' if n.causa else ''), n.get_gravedad_display(),
            n.get_disposicion_display(), n.get_estado_display(), _texto(n.cerrada_en)]
        texto_acciones = ' '.join(f'{a.descripcion} {a.verificacion} {a.responsable or ""}' for a in tareas)
        if (buscar and n.control_id not in seleccionados
                and buscar.casefold() not in (' '.join(map(str, valores)) + ' ' + texto_acciones).casefold()):
            continue
        hallazgos.append(valores)
        acciones.extend([[n.codigo, a.descripcion,
            (a.responsable.get_full_name() or a.responsable.get_username()) if a.responsable_id else 'Sin asignar',
            _texto(a.fecha_compromiso), _texto(a.fecha_cierre), a.get_estado_display(), a.verificacion or '—']
            for a in tareas])
        capturas.append(dict(modelo='no_conformidad', id=n.pk, codigo=n.codigo, control=n.control_id,
            lote_producto=n.lote_producto_id, lote_consumible=n.lote_consumible_id, objeto=objeto,
            descripcion=n.descripcion, causa=n.causa, gravedad=n.gravedad, disposicion=n.disposicion,
            estado=n.estado, detectada_en=n.detectada_en, cerrada_en=n.cerrada_en,
            acciones=[dict(id=a.pk, descripcion=a.descripcion, responsable=a.responsable_id,
                nombre_responsable=(a.responsable.get_full_name() or a.responsable.get_username())
                    if a.responsable_id else '', fecha_compromiso=a.fecha_compromiso,
                fecha_cierre=a.fecha_cierre, estado=a.estado, verificacion=a.verificacion) for a in tareas]))
    tablas = [dict(titulo='No conformidades del período y pendientes anteriores',
        headers=['Referencia', 'Detección', 'Lote / proceso', 'Hallazgo y causa', 'Gravedad',
                 'Disposición', 'Estado actual', 'Cierre'], rows=hallazgos[:500],
                 truncated=len(hallazgos) > 500, total=len(hallazgos)),
        dict(titulo='Acciones correctivas y verificación de cierre',
        headers=['No conformidad', 'Acción', 'Responsable', 'Compromiso', 'Cierre',
                 'Estado actual', 'Verificación'], rows=acciones[:500],
                 truncated=len(acciones) > 500, total=len(acciones))]
    return tablas, capturas


def dataset_perfil(categoria, unidad, inicio, fin, estado='', buscar=''):
    tipo, subtipo = CATEGORIA_RESULTADO[categoria]
    corte = min(fin, timezone.localdate())
    evidencias = list(EvidenciaGestionUnidad.objects.filter(unidad=unidad, tipo=tipo,
        fecha__range=(inicio, corte)).select_related('recurso', 'responsable', 'validado_por')) if tipo else []
    evidencias = [e for e in evidencias if isinstance(e.detalle, dict) and
        (e.detalle.get('subtipo') == subtipo or categoria == 'control-calidad' and e.detalle.get('subtipo') == 'sin_produccion')]
    validas = evidencias_verificadas(unidad, evidencias, inicio, corte) if tipo and habilitada() else []
    ids_validas = {e.pk for e in validas if not e.demostracion}
    medidas = medir_perfiles(unidad, inicio, corte, validas) if tipo and habilitada() else {}
    refs = {'publicacion': 'publicacion_id', 'datos': 'indicador_id', 'ensayo': 'ciclo_id',
            'control_calidad': 'control_id', 'produccion': 'orden_id'}
    revisados = {e.detalle.get(refs[subtipo]) for e in validas if e.pk in ids_validas} if subtipo in refs else set()
    headers, rows, tablas, capturas, capturas_no_conformidades = [], [], [], [], []
    opciones = (('validado', 'Con revisión técnica vigente'), ('pendiente', 'Revisión técnica pendiente'))
    # Lo que dice la última columna de un registro conforme y los nombres de las tres tarjetas.
    conforme, tarjetas = 'Revisión técnica vigente', ('Registros de origen', 'Con revisión técnica', 'Revisión pendiente')
    def agregar(identificador, valores, datos):
        revision = identificador in revisados
        if estado == 'validado' and not revision or estado == 'pendiente' and revision:
            return False
        if buscar and buscar.casefold() not in ' '.join(map(str, valores)).casefold():
            return False
        rows.append([*valores, 'Revisión técnica vigente' if revision else 'Revisión técnica pendiente'])
        capturas.append(datos)
        return True
    if categoria == 'boletines' and base_perfil(unidad) == 'observatorios':
        from django.db.models import Q
        from apps.observatorios.operacion.models.observatorios import PublicacionObservatorio
        headers = ['Publicación', 'Tipo', 'Período analizado', 'Fecha prevista', 'Fecha publicada', 'Estado', 'Indicadores', 'Revisión documental']
        publicaciones = PublicacionObservatorio.objects.filter(unidad=unidad).filter(
            Q(fecha_planificada__range=(inicio, fin)) | Q(fecha_publicada__range=(inicio, corte))).prefetch_related('indicadores')
        consulta_publicaciones = []
        for p in publicaciones:
            indicadores = list(p.indicadores.all())
            incluido = agregar(p.pk, [p.titulo, p.get_tipo_display(), p.periodo, _texto(p.fecha_planificada),
                _texto(p.fecha_publicada), p.get_estado_display(), ', '.join(i.codigo for i in indicadores)],
                dict(id=p.pk, titulo=p.titulo, periodo=p.periodo, estado=p.estado, fecha=p.fecha_publicada,
                     resumen=p.resumen, enlace=p.enlace, archivo=p.archivo.name,
                     indicadores=[i.pk for i in indicadores]))
            if incluido:
                consulta_publicaciones.append([p.titulo, p.archivo.url if p.archivo else p.enlace or 'Sin documento publicado'])
        tablas.append(_tabla_perfil('Consulta de los documentos publicados',
            ['Publicación', 'Archivo o enlace de consulta'], consulta_publicaciones))
    elif categoria == 'datos-observatorio' and base_perfil(unidad) == 'observatorios':
        from apps.observatorios.operacion.models.observatorios import IndicadorObservatorio
        headers = ['Serie / indicador', 'Periodicidad', 'Unidad', 'Fuente', 'Datos incorporados en el semestre', 'Última referencia', 'Revisión documental']
        metodologia, valores_rows = [], []
        for i in IndicadorObservatorio.objects.filter(unidad=unidad).prefetch_related('valores'):
            valores = list(i.valores.all())
            incorporados = [v for v in valores if inicio <= timezone.localdate(v.registrado) <= corte]
            ultimo = max((v.fecha for v in incorporados), default=None)
            incluido = agregar(i.pk, [f'{i.codigo} · {i.nombre}', i.get_periodicidad_display(), i.unidad_medida,
                          i.fuente, len(incorporados), _texto(ultimo)],
                    dict(id=i.pk, codigo=i.codigo, publicado=i.publicado, definicion=i.definicion,
                         formula=i.formula, fuente=i.fuente, periodicidad=i.periodicidad,
                         valores=[dict(id=v.pk, fecha=v.fecha, periodo=v.periodo, territorio=v.territorio,
                                       valor=v.valor, provisional=v.provisional, nota=v.nota) for v in incorporados]))
            if not incluido:
                continue
            metodologia.append([i.codigo, i.definicion, i.formula, i.desagregacion,
                                i.url_fuente or i.fuente, i.limitaciones or 'Sin limitaciones documentadas'])
            valores_rows.extend([[i.codigo, v.periodo, _texto(v.fecha), v.territorio, v.valor,
                                  'Provisional' if v.provisional else 'Definitivo', v.nota] for v in incorporados])
        tablas.extend([_tabla_perfil('Ficha metodológica y alcance de las series',
            ['Serie', 'Definición', 'Fórmula / método', 'Desagregación', 'Fuente consultable', 'Limitaciones'], metodologia),
            _tabla_perfil('Datos incorporados durante el semestre',
            ['Serie', 'Período', 'Fecha de referencia', 'Territorio', 'Valor', 'Estado', 'Fuente específica'], valores_rows)])
    elif categoria == 'ensayos' and base_perfil(unidad) == 'centro_experimental':
        headers = ['Ensayo', 'Eje', 'Parcela / área', 'Inicio', 'Fin previsto', 'Estado', 'Seguimientos del semestre', 'Revisión documental']
        seguimientos, contexto_ciclos, disenos = [], [], []
        # Solo los ciclos marcados como ensayo: la producción del centro se consulta en su propia categoría.
        for c in ciclos_del_periodo(unidad, inicio, corte, ensayos=True):
            registros = c.registros_del_periodo
            incluido = agregar(c.pk, [c.nombre, c.eje.titulo, c.lugar.nombre if c.lugar_id else 'Sin identificar',
                _texto(c.inicio), _texto(c.fin_previsto), c.get_estado_display(), len(registros)],
                dict(id=c.pk, nombre=c.nombre, eje=c.eje_id, lugar=c.lugar_id, inicio=c.inicio,
                     fin=c.fin, estado=c.estado, tipo=c.tipo, rubro=c.rubro, superficie_ha=c.superficie_ha,
                     animales=c.animales, meta=c.meta, medida=c.unidad_medida, referencia_meta=c.referencia,
                     objetivo=c.objetivo, tratamientos=c.tratamientos, repeticiones=c.repeticiones,
                     variables=c.variables, responsable_ensayo=c.responsable_id,
                     registros=[dict(id=r.pk, fecha=r.fecha, tipo=r.tipo, cantidad=r.cantidad,
                                     detalle=r.detalle, responsable=r.registrado_por_id) for r in registros]))
            if not incluido:
                continue
            contexto_ciclos.append([c.nombre, f'{c.get_tipo_display()} · {c.rubro}',
                _texto(c.superficie_ha), _texto(c.animales), _texto(c.meta), c.get_unidad_medida_display(),
                c.referencia or 'Sin referencia registrada', _texto(c.fin)])
            disenos.append([c.nombre, c.objetivo or 'Sin objetivo registrado',
                ' · '.join(linea.strip() for linea in c.tratamientos.splitlines() if linea.strip()) or 'Sin tratamientos registrados',
                _texto(c.repeticiones), c.variables or 'Sin variables registradas', _persona(c.responsable)])
            seguimientos.extend([[c.nombre, _texto(r.fecha), r.get_tipo_display(), _texto(r.cantidad),
                r.unidad_medida, r.detalle, _persona(r.registrado_por)] for r in registros])
        tablas.append(_tabla_perfil('Seguimiento, mediciones y observaciones del semestre',
            ['Ensayo', 'Fecha', 'Registro', 'Cantidad', 'Unidad', 'Resultado / observación', 'Responsable'], seguimientos))
        tablas.append(_tabla_perfil('Alcance y metas de los ensayos',
            ['Ensayo', 'Tipo / rubro', 'Superficie (ha)', 'Animales', 'Meta del ciclo',
                     'Unidad', 'Fundamento de la meta', 'Fin real'], contexto_ciclos))
        tablas.append(_tabla_perfil('Diseño de los ensayos',
            ['Ensayo', 'Objetivo', 'Tratamientos', 'Repeticiones', 'Variables que se miden', 'Responsable'], disenos))
    elif categoria == 'produccion-agropecuaria' and base_perfil(unidad) == 'centro_experimental':
        headers = ['Ciclo', 'Tipo', 'Eje / rubro', 'Área', 'Inicio', 'Fin previsto', 'Meta', 'Obtenido', 'Estado', 'Trazabilidad']
        opciones = (('validado', 'Con trazabilidad completa'), ('pendiente', 'Con datos por completar'))
        conforme, tarjetas = 'Completa', ('Ciclos productivos', 'Con trazabilidad completa', 'Con datos por completar')
        # Los ciclos que no son ensayos. No llevan revisión técnica: se comprueba que puedan seguirse.
        ciclos = ciclos_del_periodo(unidad, inicio, corte, ensayos=False)
        obtenido = produccion_de_los_ciclos(ciclos, inicio, corte)
        manejo, movimientos = [], []
        for c in ciclos:
            registros = c.registros_del_periodo
            pendientes = pendientes_de_trazabilidad(c, registros, corte)
            if estado == 'validado' and pendientes or estado == 'pendiente' and not pendientes:
                continue
            medida = c.get_unidad_medida_display()
            valores = [c.nombre, c.get_tipo_display(), f'{c.eje.titulo} · {c.rubro}',
                c.lugar.nombre if c.lugar_id else 'Sin identificar', _texto(c.inicio), _texto(c.fin_previsto),
                f'{_texto(c.meta)} {medida}', f'{_texto(obtenido[c.pk][0])} {medida}', c.get_estado_display()]
            filas = [[_texto(r.fecha), c.nombre, r.get_tipo_display(), r.detalle or '—', _texto(r.cantidad),
                r.unidad_medida or '—', r.get_destino_display() if r.destino else '—', _persona(r.registrado_por)]
                for r in registros]
            if buscar and buscar.casefold() not in ' '.join(map(str, [*valores, *(v for f in filas for v in f)])).casefold():
                continue
            rows.append([*valores, conforme if not pendientes else 'Falta: ' + ', '.join(pendientes)])
            capturas.append(dict(id=c.pk, nombre=c.nombre, eje=c.eje_id, lugar=c.lugar_id, inicio=c.inicio,
                fin_previsto=c.fin_previsto, fin=c.fin, estado=c.estado, tipo=c.tipo, rubro=c.rubro,
                superficie_ha=c.superficie_ha, animales=c.animales, meta=c.meta, medida=c.unidad_medida,
                referencia_meta=c.referencia, obtenido=obtenido[c.pk][0], pendientes=pendientes,
                registros=[dict(id=r.pk, fecha=r.fecha, tipo=r.tipo, cantidad=r.cantidad, medida=r.unidad_medida,
                                destino=r.destino, detalle=r.detalle, responsable=r.registrado_por_id)
                           for r in registros]))
            for r, fila in zip(registros, filas):
                (movimientos if r.tipo in MOVIMIENTOS_DE_PRODUCCION else manejo).append(fila)
        cabecera_registros = ['Fecha', 'Ciclo', 'Registro', 'Detalle', 'Cantidad', 'Unidad', 'Destino', 'Registrado por']
        tablas.append(_tabla_perfil('Labores, sanidad, insumos y novedades del período', cabecera_registros, manejo))
        tablas.append(_tabla_perfil('Producción obtenida, salidas y entregas del período', cabecera_registros, movimientos))
    elif categoria == 'produccion' and base_perfil(unidad) == 'plantas_piloto':
        from apps.plantas_piloto.operacion.models.produccion import OrdenProduccion
        headers = ['Orden', 'Producto', 'Origen', 'Fecha de fin', 'Estado', 'Obtenido', 'Responsable', 'Revisión documental']
        ordenes = OrdenProduccion.objects.filter(unidad=unidad, demostrativa=False,
                fecha_fin__range=(inicio, fin)).select_related('producto', 'responsable').prefetch_related('lotes')
        if estado in dict(OrdenProduccion.ESTADOS):
            ordenes = ordenes.filter(estado=estado)
        for orden in ordenes:
            agregar(orden.pk, [orden.codigo, orden.producto.nombre, orden.get_origen_display(),
                _texto(orden.fecha_fin), orden.get_estado_display(),
                f'{_texto(orden.cantidad_obtenida)} {orden.producto.unidad_medida}'.strip(),
                str(orden.responsable or 'Sin identificar')],
                dict(id=orden.pk, codigo=orden.codigo, estado=orden.estado, producto=orden.producto_id,
                     receta=orden.receta_id, fin=orden.fecha_fin, cerrado=orden.cerrada_en,
                     cantidad=orden.cantidad_obtenida, cierre=orden.detalle_cierre,
                     lotes=[dict(id=lote.pk, codigo=lote.codigo, cantidad=lote.cantidad_inicial,
                                 calidad=lote.control_calidad, estado=lote.estado) for lote in orden.lotes.all()]))
    elif categoria == 'control-calidad' and base_perfil(unidad) == 'plantas_piloto':
        from apps.plantas_piloto.operacion.models.calidad import ControlCalidad
        headers = ['Fecha', 'Plan / método', 'Lote / orden', 'Resultado registrado', 'Mediciones', 'Responsable', 'Revisión documental']
        mediciones_rows = []
        controles = ControlCalidad.objects.reales().filter(unidad=unidad, fecha__date__range=(inicio, corte)).select_related(
            'plan', 'lote_producto', 'orden', 'registrado_por').prefetch_related('mediciones__parametro')
        for c in controles:
            mediciones = list(c.mediciones.all())
            incluido = agregar(c.pk, [_texto(c.fecha), str(c.plan), c.objeto, c.get_resultado_display(), len(mediciones),
                str(c.registrado_por or 'Sin identificar')],
                dict(id=c.pk, plan=c.plan_id, lote=c.lote_producto_id, orden=c.orden_id, fecha=c.fecha,
                     resultado=c.resultado, responsable=c.registrado_por_id,
                     mediciones=[dict(parametro=m.parametro_id, valor=m.valor_numerico, texto=m.valor_texto,
                                      conforme=m.conforme) for m in mediciones]))
            if not incluido:
                continue
            mediciones_rows.extend([[c.pk, m.parametro.nombre, m.parametro.metodo, m.parametro.limite_texto,
                m.valor, 'Conforme' if m.conforme else 'No conforme'] for m in mediciones])
        tablas.append(_tabla_perfil('Métodos, límites y resultados de los controles',
            ['Control', 'Parámetro', 'Método', 'Criterio de aceptación', 'Valor observado', 'Resultado'], mediciones_rows))
        tablas_no_conformidades, capturas_no_conformidades = _tablas_no_conformidades(
            unidad, inicio, corte, revisados, {c['id'] for c in capturas}, estado, buscar)
        tablas.extend(tablas_no_conformidades)
    elif categoria == 'eventos' and base_perfil(unidad) == 'observatorios':
        headers = ['Fecha realizada', 'Actividad', 'Destinatarios', 'Participantes comprobados', 'Resultado documentado', 'Acta', 'Revisión documental']
        revisados = ids_validas
        for e in evidencias:
            if e.estado == 'anulado':
                continue
            d = e.detalle
            agregar(e.pk, [d.get('fecha_evento'), e.titulo, d.get('beneficiario'), d.get('participantes'),
                d.get('resultado'), d.get('referencia_acta')], dict(evidencia=e.pk, fecha=e.fecha, detalle=d, estado=e.estado))
    respaldos = []
    seleccionados = {c.get('id', c.get('evidencia')) for c in capturas}
    for e in evidencias:
        d = e.detalle
        # Las tablas de detalle deben respetar la misma selección del listado.
        # La justificación de cero producción no tiene un control de origen.
        if categoria == 'eventos':
            if e.pk not in seleccionados:
                continue
        elif d.get('subtipo') == 'sin_produccion':
            revisada = e.pk in ids_validas
            if estado == 'validado' and not revisada or estado == 'pendiente' and revisada:
                continue
            if buscar and buscar.casefold() not in f'{e.codigo} {e.titulo} {e.descripcion} {d}'.casefold():
                continue
        elif d.get(refs.get(subtipo)) not in seleccionados:
            continue
        revision = ('Verificado por ' + (e.validado_por.get_full_name() or e.validado_por.get_username()) +
                    ' · ' + timezone.localtime(e.validado_en).strftime('%d/%m/%Y %H:%M')) if e.pk in ids_validas else e.get_estado_display()
        respaldos.append([e.codigo, _texto(e.fecha), e.titulo, d.get('objetivo', ''), d.get('metodo', ''),
            d.get('resultado', ''), revision,
            reverse('respaldo_meta_unidad', args=[unidad.slug, e.pk]) if e.recurso_id else e.enlace or 'Sin respaldo'])
    if tipo:
        tablas.append(_tabla_perfil('Resultados, revisión técnica y documentos de respaldo',
            ['Referencia', 'Fecha', 'Actividad', 'Objetivo', 'Método de comprobación', 'Resultado y limitaciones', 'Revisión', 'Respaldo'], respaldos))
        notas = ['Las cifras acreditadas requieren respaldo vigente y comprobación atribuida a la coordinación o al responsable técnico.',
                 'La publicación o el cierre de un registro no confirma por sí solo su calidad. La valoración de metodología y conclusiones corresponde a la revisión competente.',
                 'Los borradores, ejemplos y registros alterados después de la revisión no acreditan cumplimiento.']
    else:
        notas = ['Se presentan los ciclos productivos que no son ensayos; los ensayos se consultan en su propia categoría.',
                 'La meta corresponde al ciclo completo. Lo obtenido suma cosechas, ordeños, posturas y salidas hasta el corte, en la unidad de medida de la meta; los registros presentados corresponden al período consultado.',
                 'La trazabilidad comprueba que cada ciclo y cada registro tengan los datos para seguirlos. No califica el manejo ni el rendimiento.']
    if categoria == 'ensayos':
        notas.append('Las metas corresponden al ciclo completo; los seguimientos presentados corresponden al período consultado.')
    if categoria == 'control-calidad':
        notas.append('Los estados de las no conformidades y sus acciones son los registrados actualmente.')
    conformes = sum(r[-1] == conforme for r in rows)
    return dict(headers=headers, rows=rows[:500], cards=[(tarjetas[0], len(rows)),
        (tarjetas[1], conformes), (tarjetas[2], len(rows) - conformes)],
        state_choices=opciones, tablas=tablas, supporting_documents=[], matrix=False,
        matrix_kind='', structured=False, records=[], column_count=max(1, len(headers)),
        document_meta={}, truncated=len(rows) > 500 or any(t.get('truncated') for t in tablas),
        notes=notas, fuentes_nativas=capturas + capturas_no_conformidades, mediciones=medidas)
