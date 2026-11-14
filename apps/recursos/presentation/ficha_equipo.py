"""La ficha de un activo: qué es, qué contiene, cómo se usa y qué le ha pasado.

Reúne en un solo lugar lo que hoy está repartido: la foto y las características
del equipo en el inventario, sus accesorios, insumos y software, dónde está
instalado y con qué capacidad se reserva, cuánto se usa, su vida útil por
tiempo y por horas de operación, las fichas de estado de cada mantenimiento y
la línea de trazabilidad desde que entró al laboratorio.
"""

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from apps.recursos.models.consumibles import Consumible
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo, IncidenciaEquipo, MantenimientoEquipo, PlanMantenimientoEquipo, RepuestoMantenimiento
from apps.recursos.models.equipos import PiezaEquipo
from apps.reservas.models.reservas import Reserva
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.workflows.reservas import ESTADOS_ATENCION_EFECTIVA

from apps.gestion_unidades.presentation.api import categoria_publica_equipo
from apps.recursos.presentation.mantenimiento_panel import MESES_CORTOS, SEMAFOROS, VIDA_UTIL_ALERTA, semaforo_equipo
from apps.gestion_unidades.presentation.plantillas_ficha import ficha_estandar
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from apps.gestion_unidades.presentation.reportes_dimensiones import horas_efectivas

MESES_USO = 12
ESTADOS_RESERVA_DESCARTADOS = ('cancelada', 'rechazada', 'vencida')
AVISO_RETIRO = 'Retiro de operación; no constituye autorización administrativa o patrimonial.'

MOTIVOS_FIN_VIDA = {
    'tiempo': 'Cumple su vida útil por tiempo',
    'uso': 'Cumple su vida útil por horas de operación',
    'dano': 'Baja anticipada por daño irreparable',
    'baja': 'Ciclo cerrado: el activo ya está de baja',
}


def _meses(hoy, cantidad=MESES_USO):
    serie, anio, mes = [], hoy.year, hoy.month
    for indice in range(cantidad):
        serie.append((anio, mes, f'{MESES_CORTOS[mes]} {str(anio)[-2:]}'))
        mes -= 1
        if mes == 0:
            anio, mes = anio - 1, 12
    return list(reversed(serie))


def reservas_del_equipo(equipo, desde=None):
    """Las solicitudes que comprometieron este activo, por su código de inventario (el vigente o uno anterior)."""
    codigos = [equipo.codigo_unidad, *equipo.codigos_anteriores.values_list('codigo', flat=True)]
    # Entre comillas, como lo guarda el JSON: FAB-IMP3D-05-1 no debe contar las reservas de FAB-IMP3D-05-10.
    por_codigo = Q()
    for codigo in codigos:
        por_codigo |= Q(unidades_seleccionadas__contains=f'"{codigo}"')
    consulta = Reserva.objects.filter(
        por_codigo, laboratorio=equipo.laboratorio_id or equipo.laboratorios.values('pk').first(),
    ).exclude(estado__in=ESTADOS_RESERVA_DESCARTADOS)
    if desde:
        consulta = consulta.filter(fecha__gte=desde)
    return consulta.select_related('usuario').order_by('-fecha', '-hora_inicio')


def uso_del_equipo(equipo, hoy=None, cantidad=MESES_USO):
    """Sesiones, horas y usuarios del activo, y su reparto mes a mes."""
    hoy = hoy or timezone.localdate()
    meses = _meses(hoy, cantidad)
    desde = date(meses[0][0], meses[0][1], 1)
    reservas = list(reservas_del_equipo(equipo, desde))
    horas_mes, sesiones_mes = Counter(), Counter()
    horas_total, usuarios = 0.0, set()
    for reserva in reservas:
        clave = (reserva.fecha.year, reserva.fecha.month)
        sesiones_mes[clave] += 1
        if reserva.estado in ESTADOS_ATENCION_EFECTIVA:
            horas = horas_efectivas(reserva)
            horas_mes[clave] += horas
            horas_total += horas
        if reserva.usuario_id:
            usuarios.add(reserva.usuario_id)
    serie = [{
        'etiqueta': etiqueta,
        'sesiones': sesiones_mes.get((anio, mes), 0),
        'horas': round(horas_mes.get((anio, mes), 0.0), 1),
    } for anio, mes, etiqueta in meses]
    # Las horas acumuladas de toda la vida del activo miden su desgaste.
    acumuladas = sum(
        horas_efectivas(reserva)
        for reserva in reservas_del_equipo(equipo).filter(estado__in=ESTADOS_ATENCION_EFECTIVA)
    )
    return {
        'sesiones': len(reservas),
        'horas': round(horas_total, 1),
        'usuarios': len(usuarios),
        'serie': serie,
        'maximo': max([fila['sesiones'] for fila in serie] + [1]),
        'horas_acumuladas': round(acumuladas, 1),
        'ultimas': reservas[:8],
    }


def vida_util(equipo, horas_acumuladas, hoy=None):
    """Cuánta vida le queda al activo y por qué se cerrará su ciclo.

    Un equipo termina su vida útil por tiempo, por horas de operación o por un
    daño que obliga a darlo de baja: cuenta lo que ocurra primero.
    """
    hoy = hoy or timezone.localdate()
    por_tiempo = equipo.vida_util_consumida(hoy)
    limite_horas = equipo.vida_util_por_horas
    por_uso = round(100 * horas_acumuladas / limite_horas) if limite_horas else None
    consumida = max([valor for valor in (por_tiempo, por_uso) if valor is not None], default=None)
    if equipo.fecha_baja:
        motivo = 'dano' if equipo.motivo_baja == 'dano_irreparable' else 'baja'
    elif por_uso is not None and (por_tiempo is None or por_uso >= por_tiempo):
        motivo = 'uso'
    else:
        motivo = 'tiempo'
    return {
        'anios': equipo.vida_util_efectiva,
        'horas_limite': limite_horas,
        'horas_acumuladas': horas_acumuladas,
        'por_tiempo': por_tiempo,
        'por_uso': por_uso,
        'consumida': consumida,
        'fin_previsto': equipo.fin_vida_util,
        'motivo': motivo,
        'motivo_texto': MOTIVOS_FIN_VIDA[motivo],
        'alerta': consumida is not None and consumida >= VIDA_UTIL_ALERTA,
        'cumplida': consumida is not None and consumida >= 100,
    }


def fichas_de_estado(equipo):
    """Cada mantenimiento con lo que se hizo, sus repuestos y su costo."""
    ordenes = (
        MantenimientoEquipo.objects.filter(equipo=equipo)
        .select_related('responsable', 'plan', 'incidencia')
        .prefetch_related('repuestos')
        .order_by('-fecha_programada')
    )
    fichas = []
    for orden in ordenes:
        repuestos = list(orden.repuestos.all())
        detenido = None
        if orden.fecha_inicio and orden.fecha_fin and orden.fecha_fin > orden.fecha_inicio:
            detenido = round((orden.fecha_fin - orden.fecha_inicio).total_seconds() / 3600, 1)
        fichas.append({
            'orden': orden,
            'repuestos': repuestos,
            'costo_repuestos': sum((repuesto.costo_total for repuesto in repuestos), Decimal(0)),
            'costo_total': (orden.costo or Decimal(0)) + sum(
                (repuesto.costo_total for repuesto in repuestos), Decimal(0)),
            'horas_detenido': detenido,
        })
    return fichas


def linea_de_trazabilidad(equipo, limite=60):
    """Todo lo que le ha pasado al activo, del último hecho al primero."""
    hitos = []
    for evento in (EventoCicloVidaEquipo.objects.filter(equipo=equipo)
                   .select_related('usuario').order_by('-fecha')[:limite]):
        tono = {'registro': 'inicio', 'baja': 'baja', 'disposicion': 'baja',
                'incidencia': 'critico', 'incidencia_resuelta': 'al_dia',
                'mantenimiento': 'al_dia', 'calibracion': 'al_dia'}.get(evento.tipo, 'neutro')
        detalle = evento.descripcion
        if evento.estado_anterior and evento.estado_nuevo:
            detalle = f'{detalle} ({evento.estado_anterior} → {evento.estado_nuevo})'
        hitos.append({
            'fecha': evento.fecha,
            'titulo': evento.get_tipo_display(),
            'detalle': detalle,
            'quien': evento.usuario,
            'tono': tono,
            'tipo': evento.tipo,
        })
    for incidencia in IncidenciaEquipo.objects.filter(equipo=equipo).order_by('-fecha_reporte')[:limite]:
        hitos.append({
            'fecha': incidencia.fecha_reporte,
            'titulo': f'Incidencia: {incidencia.titulo}',
            'detalle': f'{incidencia.get_tipo_display()} · {incidencia.get_estado_display()}. '
                       f'{incidencia.descripcion}',
            'quien': incidencia.reportada_por,
            'tono': 'critico' if incidencia.detiene_operacion else 'atencion',
        })
    for orden in MantenimientoEquipo.objects.filter(equipo=equipo).order_by('-fecha_programada')[:limite]:
        hitos.append({
            'fecha': orden.fecha_fin or orden.fecha_programada,
            'titulo': f'{orden.get_tipo_display()}: {orden.titulo}',
            'detalle': f'{orden.get_estado_display()}. {orden.resultado or "Sin resultado registrado."}',
            'quien': orden.responsable,
            'tono': 'al_dia' if orden.estado == 'completado' else 'neutro',
        })
    return sorted(hitos, key=lambda hito: hito['fecha'], reverse=True)[:limite]


def registros_baja_y_sustitucion(equipos):
    """La misma lectura del activo y sus eventos para pantalla, ficha y reportes.

    Dos consultas para todo el lote. Los adjuntos se identifican como soporte
    registrado, sin presentarlos como autorización ni comprobar su contenido.
    Los eventos conservan su fecha de registro, distinta de la fecha del retiro.
    """
    equipos = list(equipos)
    claves = [equipo.pk for equipo in equipos]
    if not claves:
        return {}
    eventos = {}
    for evento in (EventoCicloVidaEquipo.objects.filter(equipo_id__in=claves)
            .filter(Q(tipo__in=('baja', 'disposicion'))
                    | Q(tipo='actualizacion', descripcion__startswith='Retiro/sustitución: '))
            .select_related('usuario').order_by('-fecha', '-pk')):
        eventos.setdefault(evento.equipo_id, []).append(dict(
            evento=evento, fecha=evento.fecha, descripcion=evento.descripcion,
            usuario=evento.usuario, evidencia=evento.evidencia,
            respaldo=Path(evento.evidencia.name).name if evento.evidencia else '',
        ))
    destinos = {equipo.reemplazado_por_id for equipo in equipos if equipo.reemplazado_por_id}
    relacionados = list(UnidadEquipo.objects.filter(
        Q(reemplazado_por_id__in=claves) | Q(pk__in=destinos))
        .select_related('equipo', 'laboratorio').order_by('codigo_unidad'))
    por_id = {equipo.pk: equipo for equipo in relacionados}
    reemplazados = {}
    for equipo in relacionados:
        if equipo.reemplazado_por_id in claves:
            reemplazados.setdefault(equipo.reemplazado_por_id, []).append(equipo)
    registros = {}
    for equipo in equipos:
        historial = eventos.get(equipo.pk, [])
        registros[equipo.pk] = dict(
            fecha=equipo.fecha_baja,
            estado='Retirado de operación' if equipo.fecha_baja else 'Sin retiro registrado',
            motivo=equipo.get_motivo_baja_display() if equipo.motivo_baja else 'Sin motivo registrado',
            justificacion=equipo.observacion_baja or '',
            reemplazo=por_id.get(equipo.reemplazado_por_id),
            reemplazados=reemplazados.get(equipo.pk, []), historial=historial,
            ultimo=historial[0] if historial else None,
            tiene_registro=bool(equipo.fecha_baja or equipo.reemplazado_por_id
                                or reemplazados.get(equipo.pk) or historial),
            aviso=AVISO_RETIRO,
            origen='Datos actuales del inventario y eventos registrados del ciclo de vida.',
        )
    return registros


def resumen_baja_y_sustitucion(registro):
    """Bloque legible en la columna Situación; no añade columnas al PDF/Excel."""
    partes = []
    if registro['fecha']:
        partes = [f'Retiro operativo: {registro["fecha"]:%d/%m/%Y}',
                  f'Motivo: {registro["motivo"]}',
                  f'Referencia / justificación: {registro["justificacion"] or "Sin registrar"}']
        reemplazo = registro['reemplazo']
        partes.append(f'Reemplazo registrado: {reemplazo.codigo_unidad} · {reemplazo.equipo.nombre}'
                      if reemplazo else 'Sin reemplazo registrado')
        ultimo = registro['ultimo']
        partes.append(f'Último evento: {timezone.localtime(ultimo["fecha"]):%d/%m/%Y %H:%M}; '
                      f'registrado por {_nombre_actor(ultimo["usuario"])}; '
                      f'adjunto: {ultimo["respaldo"] or "Sin adjunto"}'
                      if ultimo else 'Sin evento de retiro registrado; origen: inventario actual')
        partes.append(registro['aviso'])
    if registro['reemplazados']:
        partes.append('Sustituye a: ' + ', '.join(e.codigo_unidad for e in registro['reemplazados']))
    return '. '.join(partes)


def _nombre_actor(usuario):
    return (usuario.get_full_name() or usuario.get_username()) if usuario else 'No registrado'


def piezas_del_equipo(equipo):
    """Las partes del equipo, con lo que se le ha cambiado a este activo.

    Una pieza no es un insumo: el filamento se gasta en el trabajo, la boquilla
    decide si el equipo imprime. Aquí van las que lo componen, las que vienen
    con él, sus herramientas y su protección eléctrica.
    """
    cambios = {}
    for repuesto in RepuestoMantenimiento.objects.filter(
            mantenimiento__equipo=equipo, pieza__isnull=False).select_related('mantenimiento'):
        cambios.setdefault(repuesto.pieza_id, []).append(repuesto)
    grupos = {}
    for pieza in PiezaEquipo.objects.filter(equipo=equipo.equipo):
        propios = sorted(cambios.get(pieza.pk, []),
                         key=lambda r: r.mantenimiento.fecha_programada, reverse=True)
        grupos.setdefault(pieza.clase, []).append({
            'pieza': pieza,
            'cambios': propios,
            'ultimo_cambio': propios[0].mantenimiento.fecha_programada if propios else None,
        })
    return [
        (clase, etiqueta, grupos.get(clase, []))
        for clase, etiqueta in PiezaEquipo.CLASES if grupos.get(clase)
    ]


def garantia_del_equipo(equipo, hoy=None):
    """Hasta cuándo responde el proveedor y qué cubre."""
    hoy = hoy or timezone.localdate()
    fin = equipo.fin_garantia
    return {
        'meses': equipo.garantia_meses,
        'fin': fin,
        'vigente': bool(fin and fin >= hoy),
        'dias_restantes': (fin - hoy).days if fin and fin >= hoy else None,
        'cobertura': equipo.garantia_cobertura,
        'contacto': equipo.garantia_contacto,
    }


def _contenido_del_equipo(equipo):
    """Insumos, software y documentación que acompañan al activo.

    Los datos del equipo salen del mismo catálogo que ve quien reserva
    (`imagen_publica_url`, accesorios y auxiliares del tipo): una sola fuente.
    """
    tipo = equipo.equipo
    insumos = list(
        Consumible.objects.filter(por_equipo__equipo=tipo, unidad_id=equipo.laboratorio_id, activo=True)
        .distinct().order_by('nombre')[:30]
    )
    # El software y los espacios se asocian al activo físico, no al tipo de equipo.
    software = list(SoftwareDisponible.objects.filter(equipos_instalados=equipo, activo=True).order_by('nombre')[:20])
    espacios = list(EspacioReservable.objects.filter(equipos_asociados=equipo, activo=True).order_by('nombre'))
    documentos = [
        (etiqueta, archivo) for etiqueta, archivo in (
            ('Manual de operación', tipo.manual_operacion),
            ('Ficha técnica', tipo.ficha_tecnica),
            ('Video de montaje y cuidados', tipo.video_montaje_cuidados),
            ('Controladores y configuración', tipo.explicacion_drivers),
        ) if archivo
    ]
    hermanos = UnidadEquipo.objects.filter(equipo=tipo, fecha_baja__isnull=True, activa=True,
                                           laboratorio_id=equipo.laboratorio_id)
    return {
        'insumos': insumos,
        'software': software,
        'espacios': espacios,
        'documentos': documentos,
        # Lo mismo que muestra el catálogo de reservas, sin duplicar el dato.
        'imagen': tipo.imagen_publica_url,
        'categoria': categoria_publica_equipo(tipo),
        'accesorios_incluidos': tipo.get_accesorios_incluidos_list(),
        'accesorios_opcionales': tipo.get_accesorios_opcionales_list(),
        'auxiliares': list(tipo.auxiliares.filter(estado='disponible').order_by('nombre')),
        'unidades_totales': hermanos.count(),
        'unidades_disponibles': hermanos.filter(estado_unidad='disponible').count(),
    }


def ficha_equipo(equipo, hoy=None):
    """Todo lo que la ficha del activo muestra, en el orden en que se lee."""
    hoy = hoy or timezone.localdate()
    planes = list(PlanMantenimientoEquipo.objects.filter(equipo=equipo, activo=True)
                  .select_related('responsable').order_by('proxima_ejecucion'))
    incidencias = list(IncidenciaEquipo.objects.filter(equipo=equipo)
                       .select_related('asignada_a').order_by('-fecha_reporte')[:12])
    abiertas = [i for i in incidencias if i.estado not in IncidenciaEquipo.ESTADOS_CERRADOS]
    vencidos = [p for p in planes if p.proxima_ejecucion < hoy]
    por_vencer = [p for p in planes if hoy <= p.proxima_ejecucion <= hoy + timedelta(days=p.anticipacion_dias)]
    estado, motivos = semaforo_equipo(
        equipo, hoy, planes=planes, incidencias=len(abiertas),
        vencidos=len(vencidos), por_vencer=len(por_vencer),
    )
    uso = uso_del_equipo(equipo, hoy)
    fichas = fichas_de_estado(equipo)
    retiro = registros_baja_y_sustitucion([equipo])[equipo.pk]
    return {
        'equipo': equipo,
        'tipo': equipo.equipo,
        'semaforo': estado,
        'etiqueta': SEMAFOROS[estado][0],
        'motivos': motivos,
        'planes': planes,
        'proximo': min((p.proxima_ejecucion for p in planes), default=None),
        'incidencias': incidencias,
        'incidencias_abiertas': len(abiertas),
        'uso': uso,
        'vida': vida_util(equipo, uso['horas_acumuladas'], hoy),
        'contenido': _contenido_del_equipo(equipo),
        'piezas': piezas_del_equipo(equipo),
        'garantia': garantia_del_equipo(equipo, hoy),
        'fichas': fichas,
        'costo_total': sum((ficha['costo_total'] for ficha in fichas), Decimal(0)),
        'trazabilidad': linea_de_trazabilidad(equipo),
        'reemplaza_a': retiro['reemplazados'],
        'retiro': retiro,
        'unidades_hermanas': list(
            UnidadEquipo.objects.filter(equipo=equipo.equipo, fecha_baja__isnull=True, activa=True,
                                        laboratorio_id=equipo.laboratorio_id)
            .exclude(pk=equipo.pk).order_by('codigo_unidad')[:12]
        ),
    }


def _equipo_de_la_unidad(request, slug, equipo_id):
    """El activo y su unidad, solo para quien gestiona el mantenimiento o los recursos."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not (puede_operar_modulo_unidad(request.user, unidad, 'mantenimiento')
            or puede_operar_modulo_unidad(request.user, unidad, 'recursos')):
        raise PermissionDenied('No tienes autorización para ver la ficha de este equipo.')
    equipo = get_object_or_404(
        UnidadEquipo.objects.select_related('equipo', 'laboratorio', 'reemplazado_por')
        .prefetch_related('equipo__categorias'),
        Q(laboratorio=unidad) | Q(laboratorios=unidad), pk=equipo_id,
    )
    return unidad, equipo


# Cada vertical administra sus expedientes en su propia sección; el espacio
# común queda de respaldo para quien administra toda la plataforma.
ESPACIOS_DE_ADMINISTRACION = {
    'laboratorios': 'laboratorios',
    'observatorios': 'observatorios',
    'centro_experimental': 'centros_experimentales',
    'plantas_piloto': 'plantas_piloto',
}


def pantalla_de_edicion(usuario, unidad, modelo, *, pk=None, filtro=''):
    """La pantalla donde se edita ese dato, solo si quien mira puede entrar.

    Se prueba primero la sección de la vertical de la unidad y después la
    común: así el enlace lleva al sitio donde esa persona sí tiene permiso,
    y si no tiene ninguno no se ofrece un enlace que terminaría en un aviso.
    """
    espacios = (ESPACIOS_DE_ADMINISTRACION.get(unidad.dependencia, ''), 'recursos')
    for espacio in espacios:
        if not espacio or not usuario.has_perm(f'{espacio}.change_{modelo}'):
            continue
        try:
            if pk is not None:
                return reverse(f'admin:{espacio}_{modelo}_change', args=[pk])
            return reverse(f'admin:{espacio}_{modelo}_changelist') + filtro
        except NoReverseMatch:
            continue
    return ''


def origenes_de_la_ficha(unidad, equipo, usuario):
    """De dónde sale cada bloque de la ficha y por dónde se corrige.

    La ficha no inventa datos: los reúne. Decirlo en cada tarjeta evita que
    alguien los vuelva a escribir en otro sitio y deja claro qué se edita a
    mano y qué se calcula solo con lo ya registrado.
    """
    tipo = equipo.equipo
    seguimiento = reverse('gestion_unidad', args=[unidad.slug]) + '?view=mantenimiento'
    recursos = reverse('gestion_unidad', args=[unidad.slug]) + '?view=recursos'
    return {
        'tipo': {
            'texto': _('La fotografía, la categoría, las características y los accesorios salen de '
                       'la ficha técnica del equipo en el catálogo: son los mismos que ve quien lo '
                       'reserva y los comparten todos los activos de este tipo.'),
            'url': pantalla_de_edicion(usuario, unidad, 'equiposservicios', pk=tipo.pk),
            'etiqueta': _('Editar la ficha técnica del equipo'),
        },
        'activo': {
            'texto': _('La serie, la ubicación, el estado, la criticidad, la adquisición y la '
                       'garantía son de este activo y solo de él.'),
            'url': pantalla_de_edicion(usuario, unidad, 'unidadequipo', pk=equipo.pk),
            'etiqueta': _('Editar este activo'),
        },
        'vida': {
            'texto': _('La vida útil prevista sale de este activo y, si no la declara, de la vida '
                       'útil de referencia del tipo de equipo. Las horas de operación se cuentan '
                       'solas con las reservas atendidas. La baja se registra en el activo.'),
            'url': pantalla_de_edicion(usuario, unidad, 'unidadequipo', pk=equipo.pk),
            'etiqueta': _('Editar vida útil, garantía y baja'),
        },
        'uso': {
            'texto': _('Se calcula solo con las reservas atendidas de este equipo y con el espacio '
                       'desde el que se reserva. No se escribe a mano.'),
            'url': recursos,
            'etiqueta': _('Ver los espacios y recursos de la unidad'),
        },
        'insumos': {
            'texto': _('Los insumos son los compatibles registrados en el inventario; el software '
                       'y los espacios, los recursos de la unidad.'),
            'url': pantalla_de_edicion(usuario, unidad, 'consumibleporequipo',
                                        filtro=f'?equipo__id__exact={tipo.pk}'),
            'etiqueta': _('Administrar los insumos compatibles'),
        },
        'piezas': {
            'texto': _('Las piezas se registran una vez por tipo de equipo, así que valen para '
                       'todos sus activos; los cambios que se ven aquí son los repuestos de las '
                       'órdenes de este activo.'),
            'url': pantalla_de_edicion(usuario, unidad, 'piezaequipo',
                                        filtro=f'?equipo__id__exact={tipo.pk}'),
            'etiqueta': _('Administrar las piezas de este tipo de equipo'),
        },
        'mantenimiento': {
            'texto': _('El plan y las órdenes se registran en el seguimiento de la unidad; cada '
                       'ficha de estado es la orden con su resultado, su ejecutor y sus repuestos.'),
            'url': seguimiento,
            'etiqueta': _('Ir al seguimiento para registrar o corregir'),
        },
        'trazabilidad': {
            'texto': _('Se arma sola con el ingreso del activo, sus cambios de estado, sus '
                       'incidencias, sus mantenimientos y su baja. No se edita.'),
            'url': '',
            'etiqueta': '',
        },
    }


@login_required
@require_http_methods(['GET'])
def ficha_equipo_view(request, slug, equipo_id):
    """La ficha del activo dentro de la consola de la unidad."""
    unidad, equipo = _equipo_de_la_unidad(request, slug, equipo_id)
    return render(request, 'portal/pages/unidades/gestion/ficha_equipo.html', {
        'page_key': 'ficha-equipo',
        'page_title': f'{equipo.codigo_unidad} · {unidad.nombre}',
        'unidad': unidad,
        'ficha': ficha_equipo(equipo),
        'url_panel': reverse('gestion_unidad', args=[unidad.slug]) + '?view=mantenimiento',
        'url_pdf': reverse('ficha_equipo_unidad_pdf', args=[unidad.slug, equipo.pk]),
        'url_pdf_retiro': reverse('ficha_equipo_unidad_pdf', args=[unidad.slug, equipo.pk]) + '?documento=baja',
        'origenes': origenes_de_la_ficha(unidad, equipo, request.user),
        'estandar': ficha_estandar(equipo.equipo, gestor=True),
    })


@login_required
@require_http_methods(['GET'])
def ficha_equipo_pdf_view(request, slug, equipo_id):
    """La misma ficha en PDF, con el marco institucional de la documentación."""
    from django.http import HttpResponse

    from apps.recursos.presentation.ficha_equipo_pdf import render_ficha_equipo_pdf

    unidad, equipo = _equipo_de_la_unidad(request, slug, equipo_id)
    solo_retiro = request.GET.get('documento') == 'baja'
    contenido = render_ficha_equipo_pdf(unidad, ficha_equipo(equipo), solo_retiro=solo_retiro)
    respuesta = HttpResponse(contenido, content_type='application/pdf')
    prefijo = 'registro-retiro' if solo_retiro else 'ficha'
    respuesta['Content-Disposition'] = f'inline; filename="{prefijo}-{equipo.codigo_unidad}.pdf"'
    return respuesta
