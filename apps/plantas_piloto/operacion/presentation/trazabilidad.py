"""Trazabilidad: de dónde salió cada lote y a dónde fue, y el consolidado institucional.

Un lote de producto se explica hacia atrás (el proceso que lo hizo, la sesión o
el encargo que lo pidió, los lotes de insumo que se consumieron y de qué pedido
llegó cada uno) y hacia adelante (los controles de calidad que pasó y los
movimientos con los que salió de la unidad). Esa cadena es lo que una planta de
alimentos tiene que poder mostrar cuando alguien pregunta por un lote.

El reporte institucional pone una fila por unidad con lo que cada una hizo en el
período: atención, producción, calidad y aula, sin abrir el panel de cada una.
"""

from datetime import timedelta
from decimal import Decimal
from functools import lru_cache

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Case, CharField, Count, DecimalField, F, Func, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.fields.json import KeyTextTransform, KeyTransform
from django.db.models.functions import Greatest, Length, Replace
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET
from django.views.decorators.cache import never_cache
from apps.gestion_unidades.presentation.reportes_filtros import PeriodoReporte
from apps.formacion.presentation.reportes_cursos import NOTAS_FORMACION, indicadores_formacion, _ventana

from apps.plantas_piloto.operacion.models.calidad import ControlCalidad, NoConformidad
from apps.recursos.models.consumibles import EntradaInventario
from apps.plantas_piloto.operacion.models.planificacion import EntregaPedido
from apps.formacion.models.aula import IntentoEjercicio
from apps.plantas_piloto.operacion.models.produccion import LoteProducto, OrdenProduccion
from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad

from apps.documentos.presentation.documentos_gestion import render_documento_oficial
from apps.gestion_unidades.presentation.permisos import unidades_gestionables, puede_operar_modulo_unidad
from apps.plantas_piloto.operacion.presentation.sesiones_erp import puede_consultar_en


NOTAS_OPERACION = (
    'Reservas: fecha programada; atenciones con cierre atendido y ejecución registrada. Las participaciones suman asistentes por atención, no personas únicas.',
    'Producción: corridas terminadas iniciadas en el período; lotes por fecha de producción.',
    'Calidad: controles por fecha del control; no conformidades abiertas en su estado actual.',
    'Aula: ejercicios con intentos asignados, entregados o calificados en el período; entregas por fecha de calificación.',
    'Los estados de corridas y lotes son actuales; no reconstruyen el estado que tenían al terminar el período.',
)


# ------------------------------------------------------- la cadena de un lote
def _consumos_de_la_orden(orden):
    """Consumos y evidencia de recepción en tres consultas, sin consultas por fila."""
    if orden is None:
        return []
    entrega = (EntregaPedido.objects.filter(entrada__lote_inventario_id=OuterRef('lote_inventario_id'))
               .order_by('fecha', 'pk').values('pk')[:1])
    control = (ControlCalidad.objects.filter(lote_consumible_id=OuterRef('lote_inventario_id'))
               .order_by('-fecha', '-pk').values('pk')[:1])
    salidas = list(
        EntradaInventario.objects.filter(
            clave_idempotencia__startswith=f'orden-produccion-{orden.pk}-', tipo='salida',
        ).select_related('consumible', 'lote_inventario', 'usuario')
        .annotate(_entrega_id=Subquery(entrega), _control_id=Subquery(control))
        .order_by('consumible__nombre', 'pk')
    )
    entregas = {fila.pk: fila for fila in EntregaPedido.objects.filter(
        pk__in={salida._entrega_id for salida in salidas if salida._entrega_id is not None},
    ).select_related('pedido')}
    controles = {fila.pk: fila for fila in ControlCalidad.objects.filter(
        pk__in={salida._control_id for salida in salidas if salida._control_id is not None},
    ).select_related('plan')}
    filas = []
    for salida in salidas:
        lote = salida.lote_inventario
        entrega = entregas.get(salida._entrega_id)
        filas.append({
            'salida': salida, 'consumible': salida.consumible, 'lote': lote,
            'entrega': entrega, 'pedido': entrega.pedido if entrega is not None else None,
            'control': controles.get(salida._control_id),
            'del_cliente': bool(lote is not None and lote.material_cliente),
        })
    return filas


def trazabilidad_de_lote(lote):
    """La genealogía completa de un lote de producto: de dónde vino y a dónde fue."""
    orden = lote.orden
    reserva = orden.reserva if orden is not None else None
    controles = list(
        ControlCalidad.objects.filter(lote_producto=lote)
        .select_related('plan', 'registrado_por')
        .prefetch_related('mediciones__parametro')
        .order_by('fecha', 'pk')
    )
    movimientos = list(
        lote.movimientos.select_related('unidad_destino', 'registrado_por', 'cliente').order_by('fecha', 'pk')
    )
    etapas = list(orden.receta.etapas.select_related('equipo', 'espacio').order_by('orden')) if orden else []
    return {
        'lote': lote,
        'orden': orden,
        'reserva': reserva,
        'receta': orden.receta if orden is not None else None,
        'consumos': _consumos_de_la_orden(orden),
        'etapas': etapas,
        'puntos_de_control': [etapa for etapa in etapas if etapa.punto_critico or etapa.punto_control],
        'equipos': list(orden.equipos.select_related('equipo').all()) if orden is not None else [],
        'controles': controles,
        'no_conformidades': list(
            NoConformidad.objects.filter(lote_producto=lote).prefetch_related('acciones').order_by('pk')
        ),
        'movimientos': movimientos,
        'entregado': sum((Decimal(movimiento.cantidad) for movimiento in movimientos), Decimal('0')),
    }


def lotes_trazables(unidad, buscado=''):
    """Los lotes de producto que la unidad puede rastrear, filtrados por su código."""
    lotes = (
        LoteProducto.objects.filter(unidad=unidad)
        .select_related('producto', 'orden')
        .order_by('-fecha_produccion', '-pk')
    )
    if buscado:
        lotes = lotes.filter(Q(codigo__icontains=buscado) | Q(producto__nombre__icontains=buscado))
    return list(lotes[:40])


# ------------------------------------------------- el consolidado institucional
def unidades_reportables(usuario):
    """Misma delegación reportes que protege el detalle y las descargas por unidad."""
    unidades = unidades_gestionables(usuario).order_by('nombre')
    if usuario.is_superuser:
        return unidades
    ids = [u.pk for u in unidades if puede_operar_modulo_unidad(usuario, u, 'reportes')]
    return Unidad.objects.filter(pk__in=ids).order_by('nombre')


@lru_cache(maxsize=1)
def _alfabeto_entero():
    """Normaliza los dígitos decimales y espacios que admite int() de Python.

    Se calcula solo al solicitar el primer reporte, una vez por proceso.
    """
    import sys
    import unicodedata
    pares = []
    for codigo in range(sys.maxunicode + 1):
        caracter = chr(codigo)
        digito = unicodedata.decimal(caracter, None)
        if digito is not None:
            pares.append((caracter, str(digito)))
        elif caracter.isspace():
            try:
                int(caracter + '0' + caracter)
            except ValueError:
                continue
            pares.append((caracter, ' '))
    return ''.join(p[0] for p in pares), ''.join(p[1] for p in pares)


def _asistencia_real(qs):
    """Equivalente agregado de participantes(), sin cast de JSON inválido.

    numeric sin precisión fija evita desbordar bigint con datos heredados.
    Los números JSON admiten la truncación de int(float); los textos solo
    admiten enteros. El límite de dígitos es el de int() de Python.
    """
    import sys
    limite = sys.get_int_max_str_digits()
    origen, destino = _alfabeto_entero()
    qs = qs.annotate(
        _asistentes_texto=KeyTextTransform('asistentes_total', 'detalle_ejecucion'),
        _asistentes_tipo=Func(KeyTransform('asistentes_total', 'detalle_ejecucion'),
                              function='jsonb_typeof', output_field=CharField()),
    ).annotate(_asistentes_normalizados=Func(F('_asistentes_texto'), Value(origen), Value(destino),
        function='translate', output_field=CharField())
    ).annotate(_asistentes_digitos=Length(Func(F('_asistentes_normalizados'), Value('[^0-9]'),
        Value(''), Value('g'), function='regexp_replace', output_field=CharField())))
    entero_textual = Q(_asistentes_tipo='string',
        _asistentes_normalizados__regex=r'^[[:space:]]*[+-]?[0-9]+(_[0-9]+)*[[:space:]]*$')
    if limite:
        entero_textual &= Q(_asistentes_digitos__lte=limite)
    numero_textual = Func(Replace(F('_asistentes_normalizados'), Value('_'), Value('')),
                  template='CAST(%(expressions)s AS numeric)', output_field=DecimalField())
    numero = Func(F('_asistentes_texto'), template='CAST(%(expressions)s AS numeric)',
                  output_field=DecimalField())
    cero = Value(0, output_field=DecimalField())
    return qs.annotate(_asistentes_reales=Case(
        When(_asistentes_tipo='number', then=Greatest(cero,
            Func(numero, function='trunc', output_field=DecimalField()))),
        When(entero_textual, then=Greatest(cero, numero_textual)),
        When(detalle_ejecucion__asistentes_total=True, then=Value(1)),
        When(Q(_asistentes_texto__isnull=True) |
             Q(detalle_ejecucion__asistentes_total__in=[None, False, '', [], {}]), then=cero),
        default=Greatest(Value(1), F('numero_participantes')), output_field=DecimalField()))


def consolidado_institucional(usuario, desde, hasta, *, unidades=None):
    """Agregados por unidad con un número fijo de consultas, sin detalle personal."""
    from apps.formacion.models.cursos import Curso
    unidades = list(unidades if unidades is not None else unidades_reportables(usuario))
    ids = [u.pk for u in unidades]
    claves = ('solicitudes', 'atendidas', 'personas', 'corridas', 'lotes', 'liberados',
              'rechazados', 'controles', 'conformes', 'no_conformidades', 'ejercicios', 'entregas',
              'cursos', 'cursos_publicados', 'cursos_nativos', 'cursos_externos', 'ediciones', 'inscripciones', 'aceptadas', 'pendientes',
              'certificados', 'horas_acreditadas')
    datos = {u.pk: {**dict.fromkeys(claves, 0), 'unidad': u, 'ingresos': Decimal('0'),
                    'panel_url': reverse('gestion_unidad', args=[u.slug])} for u in unidades}
    inicio, fin = _ventana(desde, hasta)

    def agregar(qs, campo, **metricas):
        for fila in qs.order_by().values(campo).annotate(**metricas):
            clave = fila.pop(campo)
            datos[clave].update({k: int(v or 0) if k == 'personas' else v or 0 for k, v in fila.items()})

    # Reserva.es_efectiva: cierre atendido con ejecución registrada; confirmar no es atender.
    efectiva = (Q(estado='completada', resultado_cierre='atendida',
                  detalle_ejecucion__registrada_en__isnull=False)
                & ~Q(detalle_ejecucion__registrada_en__in=['', None, False, 0, [], {}]))
    agregar(_asistencia_real(Reserva.objects.filter(laboratorio_id__in=ids, fecha__range=(desde, hasta))),
            'laboratorio_id', solicitudes=Count('pk'), atendidas=Count('pk', filter=efectiva),
            personas=Sum('_asistentes_reales', filter=efectiva))
    agregar(OrdenProduccion.objects.reales().filter(unidad_id__in=ids, fecha_inicio__range=(desde, hasta)),
            'unidad_id', corridas=Count('pk', filter=Q(estado='terminada')))
    agregar(LoteProducto.objects.reales().filter(unidad_id__in=ids, fecha_produccion__range=(desde, hasta)),
            'unidad_id', lotes=Count('pk'), liberados=Count('pk', filter=Q(control_calidad='aprobado')),
            rechazados=Count('pk', filter=Q(control_calidad='rechazado')))
    agregar(ControlCalidad.objects.reales().filter(unidad_id__in=ids, fecha__gte=inicio, fecha__lt=fin),
            'unidad_id', controles=Count('pk'), conformes=Count('pk', filter=Q(resultado='conforme')))
    agregar(NoConformidad.objects.reales().filter(unidad_id__in=ids).exclude(estado='cerrada'),
            'unidad_id', no_conformidades=Count('pk'))
    agregar(IntentoEjercicio.objects.filter(ejercicio__unidad_id__in=ids).filter(
            Q(creado_en__gte=inicio, creado_en__lt=fin)
            | Q(entregado_en__gte=inicio, entregado_en__lt=fin)
            | Q(calificado_en__gte=inicio, calificado_en__lt=fin)),
            'ejercicio__unidad_id', ejercicios=Count('ejercicio_id', distinct=True))
    agregar(IntentoEjercicio.objects.filter(ejercicio__unidad_id__in=ids, estado='calificado',
            calificado_en__gte=inicio, calificado_en__lt=fin), 'ejercicio__unidad_id', entregas=Count('pk'))
    agregar(MovimientoFinancieroUnidad.objects.filter(unidad_id__in=ids,
            fecha_movimiento__range=(desde, hasta), tipo='ingreso').exclude(estado='anulado'),
            'unidad_id', ingresos=Sum('monto'))
    formacion = indicadores_formacion(Curso.objects.filter(unidad_id__in=ids), desde, hasta)
    for clave, metricas in formacion.items():
        datos[clave].update(metricas)
    filas = list(datos.values())
    totales = {clave: sum(fila[clave] for fila in filas) for clave in claves}
    totales['ingresos'] = sum((fila['ingresos'] for fila in filas), Decimal('0'))
    totales['unidades'] = len(filas)
    totales['conformidad_pct'] = round(totales['conformes'] * 100 / totales['controles']) if totales['controles'] else None
    return {'filas': filas, 'totales': totales}


# ------------------------------------------------------------------ las vistas
def _rango(request):
    hoy = timezone.localdate()
    periodo = PeriodoReporte.pedido(request.GET, defecto=(hoy - timedelta(days=89), hoy), maximo_dias=730)
    return periodo.desde, periodo.hasta


@login_required
def trazabilidad_lote_view(request, slug, lote_id):
    """La hoja de trazabilidad de un lote: hacia atrás y hacia adelante."""
    unidad = get_object_or_404(Unidad, slug=slug)
    lote = get_object_or_404(
        LoteProducto.objects.select_related('producto', 'orden__receta', 'orden__reserva', 'orden__sesion'),
        pk=lote_id, unidad=unidad,
    )
    sesion = lote.orden.sesion if lote.orden_id else None
    if not puede_consultar_en(request.user, unidad, sesion):
        raise PermissionDenied('Solo quien opera la producción, o participa en la sesión, ve la trazabilidad.')
    contexto = trazabilidad_de_lote(lote)
    contexto.update({
        'unidad': unidad,
        'generado_en': timezone.localtime(),
        'volver_url': reverse('erp_planta', args=[unidad.slug]) + '?view=produccion' + (
            f'&sesion={sesion.codigo}' if sesion is not None else ''
        ),
        'otros_lotes': lotes_trazables(unidad, (request.GET.get('buscar') or '').strip()[:80]),
    })
    return render_documento_oficial(request, 'portal/pages/unidades/gestion/trazabilidad_lote.html', contexto)


@login_required
@require_GET
@never_cache
def reporte_institucional_view(request):
    """Consolidado autorizado; Centros I+D se abre como dominio independiente."""
    from apps.gestion_unidades.presentation.exportaciones_reportes import formato_reporte
    formato = formato_reporte(request, permitir_csv=False)
    if request.user.is_staff and not formato:
        return redirect(reverse('admin:reportes-institucional') + ('?' + request.GET.urlencode() if request.GET else ''))
    contexto = contexto_institucional(request)
    if formato:
        return exportar_institucional(contexto, formato, request.GET.get('descargar') == '1')
    return render_documento_oficial(request, 'portal/pages/unidades/gestion/reporte_institucional.html', contexto)


def contexto_institucional(request):
    """Pantalla y exportaciones comparten alcance, fechas y cifras."""
    from django.core.exceptions import BadRequest
    from apps.gestion_unidades.presentation.exportaciones_reportes import formato_reporte
    formato = formato_reporte(request, permitir_csv=False)
    unidades = list(unidades_reportables(request.user))
    acceso_centros = False
    if not formato:
        from apps.centros_id.informes import puede_reportar_centros
        acceso_centros = puede_reportar_centros(request.user)
    if not unidades and not request.user.is_superuser and (not acceso_centros or formato):
        raise PermissionDenied('No tienes autorización para reportes de unidades.')
    disponibles = unidades
    seleccion = (request.GET.get('unidad') or '').strip()
    tipo = (request.GET.get('tipo') or '').strip()
    if seleccion:
        elegida = next((u for u in unidades if seleccion in (u.slug, str(u.pk))), None)
        if elegida is None:
            raise BadRequest('Unidad fuera del alcance del reporte.')
        unidades = [elegida]
        seleccion = elegida.slug
    if tipo:
        from apps.core.presentation.tipologias import codigos_por_base, tipologias_actuales
        validos = {t.codigo for t in tipologias_actuales()}
        if tipo not in validos:
            raise BadRequest('Tipo de unidad inexistente.')
        codigos = codigos_por_base(tipo)
        unidades = [u for u in unidades if u.dependencia in codigos]
    desde, hasta = _rango(request)
    consolidado = consolidado_institucional(request.user, desde, hasta, unidades=unidades)
    export_urls = {}
    for formato in ('docx', 'xlsx'):
        parametros = request.GET.copy()
        parametros['formato'] = formato
        parametros['descargar'] = '1'
        export_urls[formato + '_url'] = '?' + parametros.urlencode()
    return {**export_urls, 'puede_reportar_centros': acceso_centros, 'solo_centros': not disponibles and acceso_centros and not request.user.is_superuser, 'consolidado': consolidado, 'filas': consolidado['filas'], 'totales': consolidado['totales'],
        'unidades_disponibles': disponibles, 'unidad_seleccionada': seleccion,
        'tipo_seleccionado': tipo, 'desde': desde, 'hasta': hasta, 'generado_en': timezone.localtime(),
        'notas_formacion': NOTAS_FORMACION, 'notas_operacion': NOTAS_OPERACION,
        'volver_url': reverse('gestion_unidad', args=[unidades[0].slug]) if unidades else reverse('admin:index') + '#reportes'}


def exportar_institucional(contexto, formato, descargar=True):
    from apps.core.reportes import respuesta_reporte
    totales = contexto['totales']
    etiquetas = [('unidades', 'Unidades'), ('solicitudes', 'Solicitudes'), ('atendidas', 'Atenciones efectivas'),
        ('personas', 'Participaciones atendidas'), ('corridas', 'Corridas terminadas'), ('lotes', 'Lotes'),
        ('controles', 'Controles de calidad'), ('conformes', 'Controles conformes'),
        ('conformidad_pct', 'Conformidad (%)'), ('liberados', 'Lotes liberados'), ('rechazados', 'Lotes rechazados'),
        ('no_conformidades', 'No conformidades abiertas'),
        ('ejercicios', 'Ejercicios con actividad'), ('entregas', 'Entregas calificadas'), ('ingresos', 'Ingresos'),
        ('cursos', 'Cursos y eventos'), ('cursos_publicados', 'Cursos y eventos publicados'),
        ('cursos_nativos', 'Actividades propias'), ('cursos_externos', 'Actividades externas'),
        ('ediciones', 'Ediciones iniciadas'),
        ('inscripciones', 'Inscripciones'), ('aceptadas', 'Inscripciones aceptadas'), ('pendientes', 'Inscripciones pendientes'),
        ('certificados', 'Certificados vigentes emitidos'), ('horas_acreditadas', 'Horas acreditadas')]
    temporal = f"{contexto['desde']:%d/%m/%Y} a {contexto['hasta']:%d/%m/%Y}"
    metricas = [{'clave': k, 'nombre': nombre, 'valor': 'Sin controles' if k == 'conformidad_pct' and totales[k] is None else totales[k],
                 'periodo': 'Estado actual' if k in ('unidades', 'cursos', 'cursos_publicados', 'cursos_nativos', 'cursos_externos', 'no_conformidades') else temporal}
                for k, nombre in etiquetas]
    filas = contexto['filas']
    reporte = {'title': 'Reporte institucional de unidades', 'scope': 'Unidades autorizadas',
        'generated_at': contexto['generado_en'], 'filter_summary': [('Período', temporal),
            ('Unidad', contexto['unidad_seleccionada'] or 'Todas las autorizadas'),
            ('Tipo', contexto['tipo_seleccionado'] or 'Todos')], 'metrics': metricas,
        'notes': [*NOTAS_OPERACION, *NOTAS_FORMACION],
        'sections': [{'titulo': 'Operación por unidad',
            'headers': ['Unidad', 'Solicitudes', 'Atenciones efectivas', 'Participantes', 'Corridas', 'Lotes', 'Controles', 'Ingresos'],
            'rows': [[f['unidad'].nombre, *[f[k] for k in ('solicitudes','atendidas','personas','corridas','lotes','controles','ingresos')]] for f in filas]},
            {'titulo': 'Calidad y aula por unidad',
            'headers': ['Unidad', 'Lotes liberados', 'Lotes rechazados', 'Controles conformes', 'No conformidades abiertas (actual)', 'Ejercicios con actividad', 'Entregas calificadas'],
            'rows': [[f['unidad'].nombre, *[f[k] for k in ('liberados','rechazados','conformes','no_conformidades','ejercicios','entregas')]] for f in filas]},
            {'titulo': 'Formación por unidad',
            'headers': ['Unidad', 'Cursos y eventos', 'Publicados', 'Ediciones iniciadas', 'Inscripciones', 'Aceptadas', 'Certificados vigentes emitidos', 'Horas acreditadas', 'Propios', 'Externos'],
            'rows': [[f['unidad'].nombre, *[f[k] for k in ('cursos','cursos_publicados','ediciones','inscripciones','aceptadas','certificados','horas_acreditadas','cursos_nativos','cursos_externos')]] for f in filas]}]}
    marco_pdf = None
    if formato == 'pdf':
        from apps.core.presentation.pdf_institucional import marco_institucional
        marco_pdf = marco_institucional(formato='REPORTE INSTITUCIONAL',
            metadatos=(f'Período: {temporal}', f"Generado: {contexto['generado_en']:%d/%m/%Y %H:%M}"),
            pie='Reporte institucional de unidades', apaisado=True)
    return respuesta_reporte(reporte, formato, f"reporte-institucional-{contexto['desde'].isoformat()}-{contexto['hasta'].isoformat()}",
                             descargar=descargar, marco_pdf=marco_pdf)
