"""Cobertura del semestre y referencia anual, sin repetir una solicitud de compras.

La propuesta presentada el año N corresponde al año N+1. Su conformidad
documental no acredita una asignación presupuestaria ni una compra autorizada.
Las consultas de este módulo no crean documentos ni movimientos financieros.
"""
from collections import Counter
from copy import deepcopy
from decimal import Decimal, DecimalException

from django.db.models import Count, Q, Sum
from django.utils.html import strip_tags


VERSION = 1
REVISION_RECURSOS = (('revisado', 'He revisado la cobertura de recursos del semestre'),)
PROPUESTA_COBERTURA = (
    '<p>Propuesta para revisión: desarrollar las actividades con los equipos, insumos, software, '
    'espacios y personal disponibles en la unidad, comprobando su condición y disponibilidad. '
    'Contrastar la referencia anual vigente con los recursos que efectivamente se hayan asignado '
    'o recibido. Identificar las limitaciones que afecten las actividades, su responsable y la '
    'medida prevista para atenderlas. Las necesidades del próximo año se presentan en el plan '
    'anual correspondiente; este apartado no constituye una nueva solicitud de compra.</p>'
)


def es_esquema_recursos(contenido):
    return (isinstance(contenido, dict)
            and type(contenido.get('recursos_periodo_version')) is int
            and contenido['recursos_periodo_version'] == VERSION)


def preparar_recursos(contenido):
    """Propone el nuevo apartado en una copia, conservando los datos anteriores."""
    resultado = deepcopy(contenido) if isinstance(contenido, dict) else {}
    primera_propuesta = not es_esquema_recursos(resultado)
    resultado['recursos_periodo_version'] = VERSION
    if primera_propuesta and not resultado.get('cobertura_recursos'):
        resultado['cobertura_recursos'] = PROPUESTA_COBERTURA
    resultado.setdefault('revision_recursos', '')
    return resultado


def _parrafo(texto, titulo=''):
    return dict(tipo='parrafo', titulo=titulo, texto=texto)


def _numero(valor):
    try:
        numero = Decimal(str(valor))
        return numero if numero.is_finite() and 0 <= numero <= Decimal('1e12') else None
    except (DecimalException, TypeError, ValueError):
        return None


def _bloques_inventario(documento):
    from apps.gestion_unidades.models.espacios import EspacioReservable
    from apps.recursos.models.consumibles import Consumible
    from apps.recursos.models.software import SoftwareDisponible
    from apps.recursos.models.unidades import UnidadEquipo

    unidad_id = documento.unidad_id
    equipos = UnidadEquipo.objects.filter(
        Q(laboratorio_id=unidad_id) | Q(laboratorios__pk=unidad_id),
        activa=True, fecha_baja__isnull=True).distinct()
    estados = Counter(equipos.values_list('estado_unidad', flat=True))
    return [dict(tipo='pares', titulo='Recursos registrados de la unidad', pares=[
        ('Equipos activos registrados', str(sum(estados.values()))),
        ('Equipos con estado disponible o en uso', str(estados['disponible'] + estados['en_uso'])),
        ('Software activo registrado', str(SoftwareDisponible.objects.filter(unidad_id=unidad_id, activo=True).count())),
        ('Insumos activos registrados', str(Consumible.objects.filter(unidad_id=unidad_id, activo=True).count())),
        ('Espacios activos registrados', str(EspacioReservable.objects.filter(unidad_id=unidad_id, activo=True).count())),
    ]), _parrafo('La ficha y el inventario orientan la revisión de cobertura. La disponibilidad funcional, '
                  'las existencias y la asignación para cada actividad se confirman en sus registros operativos.')]


def _plan_anual(documento):
    from apps.documentos.models.expediente import DocumentoExpediente

    return DocumentoExpediente.objects.filter(unidad_id=documento.unidad_id,
        anio=documento.anio - 1, exigido__codigo='PLAN-COMPRAS-ANUAL', corte='', mes__isnull=True,
    ).select_related('exigido', 'recurso', 'unidad').order_by('-pk').first()


def _constancia_anual(anual):
    from apps.documentos.models.constancias import ConstanciaDocumento

    if not anual.recurso_id:
        return None
    return ConstanciaDocumento.objects.filter(documento_id=anual.pk, recurso_id=anual.recurso_id,
        version=anual.version, sha256=anual.recurso.hash_sha256).first()


def _estado_anual(anual, constancia):
    if anual.estado == 'observado' or constancia and constancia.observado_en:
        return 'Propuesta devuelta para corrección'
    if anual.recurso_id and (not anual.recurso.activo or anual.recurso.estado == 'obsoleto'):
        return 'Referencia retirada; requiere revisión'
    if anual.estado == 'validado':
        if constancia and constancia.enviado_en and constancia.aprobado_en:
            return 'Propuesta con conformidad documental de Dirección'
        from .conformidad_lectura import completar_conformidades, lectura_conformidad
        completar_conformidades([anual])
        if lectura_conformidad(anual)['estado'] == 'conforme':
            return 'Propuesta con conformidad documental'
        return 'Propuesta enviada; conformidad pendiente'
    if anual.recurso_id:
        return 'Propuesta preparada; pendiente de envío'
    return 'Borrador de necesidades; pendiente de emisión y envío'


def _tabla_referencia(bloque):
    """Reduce el detalle anual emitido a sus datos de referencia para el semestre."""
    cabecera = bloque.get('cabecera') or []
    filas = bloque.get('filas') or []
    if not isinstance(cabecera, list) or not isinstance(filas, list):
        return None
    nombre_item = 'Bien o servicio' if 'Bien o servicio' in cabecera else 'Ítem'
    nombres = ((nombre_item, 'Área', 'Cantidad', 'Total (USD)', 'Mes', 'Semestre')
               if 'Mes' in cabecera or 'Semestre' in cabecera else
               (nombre_item, 'Cantidad', 'Total (USD)', 'Trimestre'))
    indices = [cabecera.index(nombre) for nombre in nombres if nombre in cabecera]
    if len(indices) < 2 or nombre_item not in cabecera:
        return None
    cuerpo = []
    for fila in filas:
        if not isinstance(fila, list):
            continue
        valores = [str(fila[i]) if i < len(fila) else '' for i in indices]
        if fila and str(fila[0]).casefold().startswith('total'):
            valores = ['Total propuesto' if cabecera[i] == nombre_item else
                       str(fila[i]) if cabecera[i] == 'Total (USD)' and i < len(fila) else '' for i in indices]
        cuerpo.append(valores)
    return dict(tipo='tabla', titulo='Necesidades del año de ejecución: referencia documental',
                cabecera=[nombre for nombre in nombres if nombre in cabecera], filas=cuerpo)


def _detalle_anual(anual, constancia):
    if constancia and isinstance(constancia.contenido_emitido, dict) and constancia.contenido_emitido:
        secciones = constancia.contenido_emitido.get('secciones') or []
        bloques = []
        for seccion in secciones if isinstance(secciones, list) else []:
            if not isinstance(seccion, dict) or seccion.get('codigo') != 'compras':
                continue
            for bloque in seccion.get('bloques') or []:
                if not isinstance(bloque, dict):
                    continue
                if bloque.get('tipo') == 'tabla':
                    tabla = _tabla_referencia(bloque)
                    if tabla:
                        bloques.append(tabla)
                elif bloque.get('tipo') in ('parrafo', 'vacio') and bloque.get('texto'):
                    bloques.append(_parrafo(str(bloque['texto'])))
                elif bloque.get('tipo') == 'rico' and bloque.get('html'):
                    bloques.append(_parrafo(strip_tags(str(bloque['html'])).strip()))
        return bloques or [_parrafo('El detalle de necesidades no está disponible en la constancia emitida. '
                                    'Consulte el documento anual de referencia.')]

    # Un borrador puede orientar el semestre, pero siempre se identifica como tal.
    # Una entrega externa sin contenido emitido no se reconstruye desde un borrador.
    if anual.recurso_id:
        return [_parrafo('Consulte el archivo anual de referencia para revisar las necesidades. '
                         'Esta entrega no conserva un detalle emitido que pueda trasladarse automáticamente.')]
    from apps.documentos.models.expediente import DocumentoElaborado
    from .presupuesto_documental import analizar_presupuesto
    redaccion = DocumentoElaborado.objects.filter(documento_id=anual.pk).first()
    contenido = redaccion.contenido if redaccion and isinstance(redaccion.contenido, dict) else {}
    lectura = analizar_presupuesto('compras', contenido)
    if contenido.get('pac_version') == 2:
        from .pac_universitario import MESES_COMPRA, semestre_compra
        filas = [[str(f.get('item') or 'Sin descripción'), str(f.get('area_nombre') or 'Por confirmar'),
                  str(f.get('cantidad') or ''), dict(MESES_COMPRA).get(str(f.get('mes_compra')), 'Por confirmar'),
                  str(semestre_compra(f.get('mes_compra')) or 'Por confirmar')] for f in lectura['filas']]
        return ([dict(tipo='tabla', titulo='Necesidades en borrador: referencia sin aprobación',
                      cabecera=['Bien o servicio', 'Área', 'Cantidad propuesta', 'Mes previsto', 'Semestre'], filas=filas)]
                if filas else [_parrafo('El borrador anual todavía no contiene adquisiciones definidas.')])
    filas = [[str(f.get('item') or 'Sin descripción'), str(f.get('cantidad') or ''),
              str(f.get('trimestre') or 'Sin definir')] for f in lectura['filas']]
    return ([dict(tipo='tabla', titulo='Necesidades en borrador: referencia sin aprobación',
                  cabecera=['Ítem', 'Cantidad propuesta', 'Trimestre previsto'], filas=filas)] if filas else
            [_parrafo('El borrador anual todavía no contiene adquisiciones definidas.')])


def _bloques_anual(documento):
    anual = _plan_anual(documento)
    pares = [('Año de ejecución de referencia', str(documento.anio)),
             ('Año de elaboración de las necesidades', str(documento.anio - 1))]
    if anual is None:
        pares.append(('Referencia anual en el sistema', 'No registrada para este año de ejecución'))
        detalle = [_parrafo('La ausencia de referencia anual no acredita que la unidad no requiera recursos. '
                            'Revise los recursos existentes y las asignaciones institucionales disponibles.')]
    else:
        constancia = _constancia_anual(anual)
        pares.extend([('Documento de referencia', anual.nombre_documental),
                      ('Estado de la propuesta', _estado_anual(anual, constancia))])
        detalle = _detalle_anual(anual, constancia)
    return [dict(tipo='pares', titulo='Referencia anual para el semestre', pares=pares), *detalle,
            _parrafo('La conformidad de una propuesta de necesidades no autoriza compras ni acredita '
                      'financiación. Las asignaciones y autorizaciones institucionales se comprueban '
                      'en sus documentos de respaldo.')]


def _bloques_egresos(documento, inicio, fin):
    from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad

    agregados = MovimientoFinancieroUnidad.objects.filter(unidad_id=documento.unidad_id,
        tipo='egreso', estado='confirmado', fecha_movimiento__range=(inicio, fin),
    ).values('fuente_fondos').annotate(total=Sum('monto'), registros=Count('pk')).order_by('fuente_fondos')
    fuentes = dict(MovimientoFinancieroUnidad.FUENTE_CHOICES)
    filas, total, registros = [], Decimal(0), 0
    for dato in agregados:
        importe = dato['total'] or Decimal(0)
        cantidad = dato['registros']
        total += importe
        registros += cantidad
        filas.append([fuentes.get(dato['fuente_fondos'], dato['fuente_fondos']), str(cantidad), f'{importe:,.2f}'])
    bloques = [dict(tipo='pares', titulo='Egresos confirmados registrados en el semestre', pares=[
        ('Período consultado', f'{inicio:%d/%m/%Y} – {fin:%d/%m/%Y}'),
        ('Movimientos confirmados', str(registros)), ('Total registrado (USD)', f'{total:,.2f}'),
    ])]
    if filas:
        bloques.append(dict(tipo='tabla', titulo='Egresos registrados por fuente de fondos',
            cabecera=['Fuente registrada', 'Movimientos', 'Monto (USD)'], filas=filas))
    else:
        bloques.append(_parrafo('No hay egresos confirmados registrados para la unidad en este semestre.'))
    bloques.append(_parrafo('Estos importes corresponden a movimientos registrados en el sistema. '
        'No se asignan a partidas de una propuesta anual por coincidencia de nombres y no sustituyen '
        'la liquidación presupuestaria institucional.'))
    return bloques


def _bloques_antecedente(contenido):
    guardadas = contenido.get('inversion') or []
    if not isinstance(guardadas, list):
        return []
    filas = []
    for fila in guardadas:
        if not isinstance(fila, dict) or not any(str(fila.get(c) or '').strip()
                for c in ('item', 'cantidad', 'justificacion', 'costo_unitario', 'fuente', 'prioridad')):
            continue
        cantidad, costo = _numero(fila.get('cantidad')), _numero(fila.get('costo_unitario'))
        total = f'{cantidad * costo:,.2f}' if cantidad is not None and costo is not None else 'Sin importe completo'
        filas.append([str(fila.get('item') or 'Sin descripción'), str(fila.get('cantidad') or ''), total])
    justificacion = strip_tags(str(contenido.get('sin_inversion_justificacion') or '')).strip()
    if not filas and not justificacion:
        return []
    bloques = [_parrafo('El siguiente contenido procede de la captura semestral anterior y se conserva '
                         'como antecedente. No constituye una nueva solicitud de adquisiciones.',
                         'Antecedente de la redacción anterior')]
    if filas:
        bloques.append(dict(tipo='tabla', titulo='Adquisiciones declaradas anteriormente en el semestre',
                            cabecera=['Ítem', 'Cantidad', 'Total declarado (USD)'], filas=filas))
    if justificacion:
        bloques.append(_parrafo(justificacion, 'Justificación conservada de la redacción anterior'))
    return bloques


def _bloques_actuales(documento, inicio, fin, contenido):
    return [*_bloques_inventario(documento), *_bloques_anual(documento),
            *_bloques_egresos(documento, inicio, fin), *_bloques_antecedente(contenido)]


def bloques_recursos(documento, inicio, fin, contenido):
    """Usa la captura emitida si existe; el borrador consulta las fuentes actuales."""
    contenido = contenido if isinstance(contenido, dict) else {}
    captura = contenido.get('recursos_periodo_fuentes')
    if (isinstance(captura, dict) and captura.get('version') == VERSION
            and captura.get('inicio') == inicio.isoformat() and captura.get('fin') == fin.isoformat()
            and captura.get('unidad') == documento.unidad_id and captura.get('anio') == documento.anio
            and isinstance(captura.get('bloques'), list)):
        return deepcopy(captura['bloques'])
    return _bloques_actuales(documento, inicio, fin, contenido)


def fijar_recursos(documento, inicio, fin, contenido, *, actualizar=False):
    """Copia para conservar en la redacción antes de emitir el documento nativo."""
    resultado = preparar_recursos(contenido)
    if actualizar:
        resultado.pop('recursos_periodo_fuentes', None)
    bloques = bloques_recursos(documento, inicio, fin, resultado)
    resultado['recursos_periodo_fuentes'] = dict(version=VERSION, unidad=documento.unidad_id,
        anio=documento.anio, inicio=inicio.isoformat(), fin=fin.isoformat(), bloques=deepcopy(bloques))
    return resultado
