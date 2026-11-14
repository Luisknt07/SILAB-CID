"""Lecturas de avance: preparación, conformidad y metas tienen alcances distintos.

Los listados usan fuentes ya cargadas. No se abre un PDF ni se ejecuta una
validación al consultar una barra de progreso.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def _porcentaje(valor):
    try:
        numero = Decimal(str(valor))
        if numero.is_finite() and 0 <= numero <= 100:
            return numero.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        pass
    return None


def _lectura(porcentaje, etiqueta, descripcion, alcance):
    porcentaje = _porcentaje(porcentaje)
    return dict(porcentaje=porcentaje, etiqueta=etiqueta, descripcion=descripcion,
                medido=porcentaje is not None, alcance=alcance)


def _metas(filas, *, archivado=False):
    exigibles = [f for f in filas if f.get('exigible') and f.get('aplica', True)]
    if not exigibles:
        return _lectura(None, 'Sin meta independiente',
            'Este anexo respalda registros; no añade una obligación al promedio del expediente.', 'metas')
    valores = [_porcentaje(f.get('porcentaje')) for f in exigibles]
    pendientes = any(f.get('pendiente') or not f.get('definida', True) or p is None
                     for f, p in zip(exigibles, valores))
    # Lo pendiente participa como cero en el seguimiento, sin afirmarse medido
    # ni convertirse en una meta cumplida por no tener registros.
    porcentaje = sum(p or Decimal(0) if not f.get('pendiente') and f.get('definida', True) else Decimal(0)
                     for f, p in zip(exigibles, valores)) / len(valores)
    return _lectura(porcentaje, 'Metas archivadas' if archivado else 'Metas al corte',
        ('Promedio de las metas exigibles de esta evidencia. ' +
         ('Hay mediciones pendientes; su aporte provisional es cero. ' if pendientes else '') +
         ('Corresponde al cierre enviado y conserva sus fuentes.' if archivado else
          'Seguimiento con los registros actuales; no constituye el resultado definitivo.') +
         ' Este avance no sustituye el resultado acreditado del informe.'), 'metas')


def leer_avance(documento, lectura=None):
    """Proyección pura: nunca usa una nota antigua como avance actual del plan."""
    lectura = lectura or {}
    exigido = documento.exigido
    control = getattr(documento, 'automatizacion', {}) or {}
    if getattr(documento, 'estado', '') == 'no_aplica':
        return _lectura(None, 'No aplica', 'No se requiere esta entrega en el alcance consultado.', 'no_aplica')
    indicadores = getattr(documento, 'indicadores_cierre', None)
    if indicadores is not None:
        return _metas(indicadores, archivado=bool(getattr(documento, '_avance_archivado', False)))
    if getattr(exigido, 'es_anexo', False):
        porcentaje = ((control.get('resumen') or {}).get('cumplimiento')
                      if control.get('vigente') else None)
        return _lectura(porcentaje, 'Respaldo comprobado' if porcentaje is not None else 'Sin medición',
            'Porcentaje de registros con respaldo comprobado; no es cumplimiento de la meta semestral.'
            if porcentaje is not None else
            'Se mostrará el avance cuando exista una meta o un control verificable. El archivo por sí solo no acredita 100 %.',
            'respaldo')
    if lectura.get('permanente') or getattr(exigido, 'periodicidad', '') == 'unica':
        vigente = bool((lectura.get('aprobacion') or {}).get('vigente'))
        if not lectura:
            vigente = bool((getattr(documento, 'aprobacion_permanente', {}) or {}).get('vigente'))
        return _lectura(100 if vigente else 0, 'Vigencia',
            'Aprobación única de la versión vigente. Se conserva entre períodos; no es una calificación.', 'vigencia')
    conformidad = lectura.get('conformidad')
    if conformidad is None and getattr(exigido, 'codigo', '') in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL'):
        from .conformidad_lectura import lectura_conformidad
        conformidad = lectura_conformidad(documento)
    if conformidad and conformidad['estado'] == 'conforme':
        return _lectura(100, 'Conformidad',
            'Documento conforme. No acredita la ejecución de actividades ni autoriza gastos.', 'conformidad')
    if getattr(exigido, 'codigo', '') == 'INFORME-SEMESTRAL':
        cierre = getattr(documento, '_avance_cierre', None)
        if cierre is not None:
            return _metas(cierre.get('filas', []), archivado=bool(cierre.get('congelado')))
        # La propiedad nota puede cargar controles o políticas si la instancia
        # aún no fue preparada. El listado proporciona su lectura precargada.
        nota = lectura.get('nota')
        integridad = lectura.get('integridad', getattr(documento, 'integridad_documental', {})) or {}
        if nota is not None and getattr(documento, 'estado', '') == 'validado':
            acreditada = not integridad.get('aplica') or integridad.get('correspondencia_verificada')
            return _lectura(nota if acreditada else None, 'Resultado acreditado' if acreditada else 'Por verificar',
                'Resultado del informe en escala de 0 a 100 %.' if acreditada else
                'El antecedente registrado requiere comprobar su correspondencia antes de acreditar avance.', 'metas')
        return _lectura(None, 'Metas por consultar',
            'Abra la unidad para consultar las metas al día. El consolidado utiliza resultados guardados y no '
            'confunde el porcentaje de redacción del informe con la ejecución de sus actividades.', 'metas')
    redaccion = getattr(documento, 'avance_redaccion', None)
    if redaccion is not None:
        return _lectura(redaccion, 'Preparación',
            'Apartados obligatorios completos en el editor. No acredita conformidad, firma ni cumplimiento de metas.',
            'preparacion')
    return _lectura(None, 'Sin medición', 'No hay una fuente verificable de avance para este documento.', 'sin_medicion')


def aplicar_bloqueo_preparacion(documento, lectura):
    """No ofrece aprobar una emisión QR antigua cuyos apartados están incompletos.

    Usa únicamente datos precargados y devuelve una proyección de la lectura.
    La vigencia del protocolo y las metas del informe tienen otro alcance:
    sus porcentajes no indican si el contenido está listo para aprobación.
    """
    if not isinstance(lectura, dict) or not getattr(documento, 'verificacion_qr', None):
        return lectura
    revision = lectura.get('revision_simple') or {}
    qr = lectura.get('aprobacion_qr') or revision
    preparacion = _porcentaje(getattr(documento, 'avance_redaccion', None))
    if (getattr(documento, 'estado', '') != 'validado' or not qr.get('enviado')
            or qr.get('aprobado') or qr.get('rechazado') or preparacion is None or preparacion >= 100):
        return lectura
    if not revision:
        return lectura
    resultado = dict(lectura)
    resultado['revision_simple'] = dict(revision, puede_aprobar=False,
        mensaje_bloqueo='Documento incompleto. Devuelve a la unidad para corregir y reenviar.')
    return resultado


def completar_avances(documentos, redacciones=None):
    """Una consulta por lote de redacciones; las siguientes lecturas no consultan."""
    documentos = list(documentos)
    pendientes = [d for d in documentos if getattr(d.exigido, 'redactable', False)
                  and (not hasattr(d, 'avance_redaccion') or not hasattr(d, 'pendientes_redaccion'))]
    if pendientes:
        if redacciones is None:
            from apps.documentos.models.expediente import DocumentoElaborado
            ids = [d.pk for d in pendientes if d.pk]
            redacciones = {r.documento_id: r for r in DocumentoElaborado.objects.filter(
                documento_id__in=ids).only('documento_id', 'contenido')} if ids else {}
        from .expediente_redaccion import avance, faltantes_del_editor
        for d in pendientes:
            redaccion = redacciones.get(d.pk)
            contenido = redaccion.contenido if redaccion and isinstance(redaccion.contenido, dict) else {}
            progreso = avance(d.exigido.fuente_reporte, contenido)
            d.avance_redaccion = progreso['porcentaje']
            d.pendientes_redaccion = faltantes_del_editor(progreso)
    for documento in documentos:
        lectura = getattr(documento, 'resumen_interfaz', None)
        documento.avance_documental = leer_avance(documento, lectura)
        if lectura is not None:
            lectura['avance'] = documento.avance_documental
            documento.resumen_interfaz = aplicar_bloqueo_preparacion(documento, lectura)
    return documentos


def completar_avance_de_unidad(unidad, anio, documentos, *, hoy=None):
    """Detalle de una unidad: usa exactamente el cálculo que ve su responsable.

    El consolidado no recalcula fuentes de cientos de unidades en cada GET.
    Al seleccionar una unidad se consulta su seguimiento completo, preservando
    los resultados y denominadores del listado institucional.
    """
    from .expediente import arbol_del_expediente
    arbol = arbol_del_expediente(unidad, anio, hoy=hoy)
    actuales = {d.pk: d for d in arbol['documentos'] if d.pk}
    for documento in documentos:
        fuente = actuales.get(documento.pk)
        if (not fuente or any(getattr(fuente, campo) != getattr(documento, campo) for campo in (
                'unidad_id', 'anio', 'corte', 'marco_periodo', 'tramo_inicio', 'tramo_fin', 'version', 'recurso_id'))):
            continue
        for atributo in ('_avance_cierre', 'indicadores_cierre', '_avance_archivado'):
            if hasattr(fuente, atributo):
                setattr(documento, atributo, getattr(fuente, atributo))
    completar_avances(documentos)
