"""El panel de gestión de un observatorio: lo que su equipo necesita, sin las pestañas de un laboratorio.

Un observatorio no presta equipos ni ejecuta prácticas: su trabajo diario es mantener los indicadores al día,
cumplir el calendario de publicaciones y atender las solicitudes de datos. El panel muestra eso primero y conserva
lo que comparte con las demás unidades (las visitas, el Centro de reportes y la configuración). El uso de
su sala se pide como una solicitud más, no con la agenda de reservas de un laboratorio.
"""
import csv
import io
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, OuterRef, Q, Subquery
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.observatorios.operacion.models.observatorios import IndicadorObservatorio, ValorIndicador
from apps.directorio_unidades.models.core import Unidad

from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad

# Cuántos días pueden pasar desde el inicio del periodo del último valor antes de que el indicador se considere
# atrasado: ese periodo, el siguiente (cuyo valor es el que se espera) y lo que la fuente suele tardar en publicarlo.
PLAZO_DE_ACTUALIZACION = {
    'diaria': 3, 'semanal': 17, 'mensual': 105, 'trimestral': 270, 'cuatrimestral': 335, 'semestral': 485,
    'anual': 910, 'quinquenal': 365 * 11, 'eventual': None,
}
# La navegación del panel de un observatorio: clave de la sección, nombre y grupo.
NAVEGACION_GESTION_OBSERVATORIO = (
    ('obs_indicadores', 'Indicadores y datos', 'Producción de datos'),
    ('obs_publicaciones', 'Publicaciones y calendario', 'Producción de datos'),
    ('obs_solicitudes', 'Solicitudes de datos', 'Atención'),
    ('visitas', 'Visitas', 'Atención'),
    # Sus equipos informáticos, software y sala (anexo 2) y su plan de mantenimiento (anexo 1) se registran
    # en las mismas pantallas que en un laboratorio: sin ellas esos anexos no tendrían de dónde salir.
    ('recursos', 'Equipos, software y sala', 'Unidad'),
    ('mantenimiento', 'Mantenimiento', 'Unidad'),
    ('reportes', 'Centro de reportes', 'Unidad'),
    ('configuracion', 'Configuración de la unidad', 'Unidad'),
)


def estado_de_actualizacion(indicador, ultimo, hoy=None):
    """'al_dia', 'atrasado' o 'sin_datos' según la periodicidad del indicador y la fecha de su último valor."""
    if ultimo is None:
        return 'sin_datos'
    plazo = PLAZO_DE_ACTUALIZACION.get(indicador.periodicidad)
    if plazo is None:
        return 'al_dia'
    return 'atrasado' if (hoy or timezone.localdate()) - ultimo.fecha > timedelta(days=plazo) else 'al_dia'


def contexto_gestion_observatorio(unidad, *, vista=None, pagina=1):
    """Consulta solo la sección abierta, sin materializar series ni expedientes históricos."""
    contexto = {}
    hoy = timezone.localdate()
    if vista is None or vista == 'obs_indicadores':
        ultimos = ValorIndicador.objects.filter(
            indicador=OuterRef('pk'), territorio=OuterRef('territorio_principal')
        ).order_by('-fecha', '-pk')
        indicadores = unidad.indicadores_observatorio.annotate(
            ultima_fecha=Subquery(ultimos.values('fecha')[:1]),
            ultimo_periodo=Subquery(ultimos.values('periodo')[:1]),
        )
        atrasados = Q(pk__in=[])
        for periodicidad, plazo in PLAZO_DE_ACTUALIZACION.items():
            if plazo is not None:
                atrasados |= Q(periodicidad=periodicidad, ultima_fecha__lt=hoy - timedelta(days=plazo))
        totales = indicadores.order_by().aggregate(
            indicadores=Count('pk'), publicados=Count('pk', filter=Q(publicado=True)),
            al_dia=Count('pk', filter=Q(ultima_fecha__isnull=False) & ~atrasados),
            atrasados=Count('pk', filter=atrasados),
            sin_datos=Count('pk', filter=Q(ultima_fecha__isnull=True)),
            conectados=Count('pk', filter=Q(conector__activo=True)),
        )
        consulta = indicadores.select_related('fuente_datos', 'conector').annotate(
            total_valores=Count('valores')
        ).order_by('orden', 'nombre', 'pk')
        pagina_indicadores = Paginator(consulta, 25).get_page(pagina)
        filas = []
        for indicador in pagina_indicadores:
            # La plantilla utiliza únicamente la fecha y el periodo del último valor.
            ultimo = (SimpleNamespace(fecha=indicador.ultima_fecha, periodo=indicador.ultimo_periodo) if indicador.ultima_fecha else None)
            filas.append({'indicador': indicador, 'ultimo': ultimo,
                'estado': estado_de_actualizacion(indicador, ultimo, hoy),
                'valores': indicador.total_valores, 'conector': getattr(indicador, 'conector', None)})
        contexto.update(obs_filas=filas, obs_totales=totales,
            obs_conectados=totales['conectados'], obs_pagina=pagina_indicadores,
            obs_encuestas=unidad.encuestas_observatorio.filter(activa=True).count(),
            obs_aliados=unidad.aliados_observatorio.filter(activo=True).count())
    if vista is None or vista == 'obs_publicaciones':
        from apps.observatorios.operacion.presentation.observatorio import cumplimiento
        publicaciones = unidad.publicaciones_observatorio.exclude(estado='cancelada')
        atrasadas = publicaciones.filter(estado='planificada', fecha_planificada__lt=hoy)
        proximas = publicaciones.filter(estado='planificada', fecha_planificada__gte=hoy)
        pagina_publicaciones = Paginator(atrasadas.order_by('fecha_planificada', 'pk'), 25).get_page(pagina)
        contexto.update(obs_cumplimiento=cumplimiento(unidad),
            obs_atrasadas=pagina_publicaciones.object_list,
            obs_total_atrasadas=pagina_publicaciones.paginator.count,
            obs_proximas=proximas.order_by('fecha_planificada', 'pk')[:6],
            obs_total_proximas=proximas.count(),
            obs_publicadas=publicaciones.filter(estado='publicada').order_by('-fecha_publicada', '-pk')[:6],
            obs_pagina=pagina_publicaciones)
    if vista is None or vista == 'obs_solicitudes':
        solicitudes = unidad.solicitudes_datos.all()
        duracion = ExpressionWrapper(TruncDate('atendida') - TruncDate('creada'), output_field=DurationField())
        resumen = solicitudes.order_by().aggregate(total=Count('pk'),
            abiertas=Count('pk', filter=Q(estado__in=('recibida', 'en_proceso'))),
            promedio=Avg(duracion, filter=Q(atendida__isnull=False)))
        pagina_solicitudes = Paginator(solicitudes.select_related('usuario').order_by('-creada', '-pk'), 25).get_page(pagina)
        promedio = resumen['promedio']
        contexto.update(obs_solicitudes=pagina_solicitudes.object_list,
            obs_solicitudes_abiertas=resumen['abiertas'], obs_solicitudes_total=resumen['total'],
            obs_dias_atencion=round(promedio.total_seconds() / 86400) if promedio is not None else None,
            obs_pagina=pagina_solicitudes)
    return contexto


def _fecha_de_periodo(periodo):
    """El primer día de un periodo escrito como «2024», «2025-T4», «2025-S2» o «2026-02»."""
    texto = periodo.strip().upper()
    if len(texto) == 4 and texto.isdigit():
        return date(int(texto), 1, 1)
    anio, _, parte = texto.partition('-')
    if parte.startswith('T') and parte[1:].isdigit():
        return date(int(anio), (int(parte[1:]) - 1) * 3 + 1, 1)
    if parte.startswith('S') and parte[1:].isdigit():
        return date(int(anio), 1 if parte[1:] == '1' else 7, 1)
    if parte.isdigit():
        return date(int(anio), int(parte), 1)
    raise ValueError(periodo)


def importar_valores(unidad, archivo):
    """Carga valores desde un CSV (separado por punto y coma o coma) con las columnas codigo, periodo, valor y,
    si se quiere, fecha, territorio, provisional y nota. Devuelve (creados, actualizados, errores)."""
    contenido = archivo.read().decode('utf-8-sig')
    delimitador = ';' if contenido.count(';') >= contenido.count(',') else ','
    lector = csv.DictReader(io.StringIO(contenido), delimiter=delimitador)
    columnas = {(nombre or '').strip().lower() for nombre in (lector.fieldnames or [])}
    faltan = {'codigo', 'periodo', 'valor'} - columnas
    if faltan:
        return 0, 0, [f'Faltan las columnas: {", ".join(sorted(faltan))}.']
    indicadores = {indicador.codigo: indicador for indicador in unidad.indicadores_observatorio.all()}
    creados = actualizados = 0
    errores = []
    with transaction.atomic():
        for numero, fila in enumerate(lector, start=2):
            fila = {(clave or '').strip().lower(): (valor or '').strip() for clave, valor in fila.items()}
            if not fila.get('valor'):
                continue  # Las filas de la plantilla que no se llenaron.
            indicador = indicadores.get(fila['codigo'])
            if indicador is None:
                errores.append(f'Fila {numero}: no existe el indicador «{fila["codigo"]}» en este observatorio.')
                continue
            try:
                cifra = Decimal(fila['valor'].replace(' ', '').replace(' ', '').replace(',', '.'))
                fecha = date.fromisoformat(fila['fecha']) if fila.get('fecha') else _fecha_de_periodo(fila['periodo'])
            except (InvalidOperation, ValueError):
                errores.append(f'Fila {numero}: el valor o el periodo no se entienden.')
                continue
            territorio = fila.get('territorio') or indicador.territorio_principal
            datos = {'periodo': fila['periodo'], 'valor': cifra, 'nota': fila.get('nota', '')[:255],
                     'provisional': fila.get('provisional', '').lower() in ('si', 'sí', '1', 'true', 'x')}
            valor, nuevo = ValorIndicador.objects.get_or_create(indicador=indicador, fecha=fecha, territorio=territorio,
                                                                defaults=datos)
            if not nuevo:
                for campo, dato in datos.items():
                    setattr(valor, campo, dato)
            try:
                valor.full_clean()
            except ValidationError as error:
                errores.append(f'Fila {numero}: {"; ".join(error.messages)}')
                continue
            valor.save()
            creados += nuevo
            actualizados += not nuevo
    return creados, actualizados, errores


@login_required
@require_POST
def importar_valores_view(request, slug):
    """Quien gestiona el observatorio sube un CSV con valores; vuelve al panel con el resultado."""
    unidad = get_object_or_404(Unidad, slug=slug, dependencia='observatorios')
    if not puede_gestionar_unidad(request.user, unidad):
        raise PermissionDenied('Solo quien gestiona el observatorio carga sus datos.')
    archivo = request.FILES.get('archivo')
    if archivo is None or not archivo.name.lower().endswith('.csv'):
        messages.error(request, 'Sube un archivo CSV con las columnas codigo, periodo y valor.')
    else:
        creados, actualizados, errores = importar_valores(unidad, archivo)
        resumen = f'{creados} valores nuevos y {actualizados} actualizados.'
        if errores:
            messages.warning(request, resumen + ' Revisa: ' + ' '.join(errores[:5]) + (' …' if len(errores) > 5 else ''))
        else:
            messages.success(request, resumen)
    return redirect(f"{reverse('gestion_unidad', args=[slug])}?view=obs_indicadores")


@login_required
def plantilla_csv_view(request, slug):
    """La plantilla CSV para cargar valores, con los códigos de los indicadores del observatorio."""
    from django.http import HttpResponse

    unidad = get_object_or_404(Unidad, slug=slug, dependencia='observatorios')
    if not puede_gestionar_unidad(request.user, unidad):
        raise PermissionDenied('Solo quien gestiona el observatorio carga sus datos.')
    respuesta = HttpResponse(content_type='text/csv; charset=utf-8')
    respuesta['Content-Disposition'] = f'attachment; filename="plantilla-valores-{slug}.csv"'
    respuesta.write('﻿')
    escritor = csv.writer(respuesta, delimiter=';')
    # «indicador» solo orienta a quien llena la plantilla: la importación lo ignora.
    escritor.writerow(['codigo', 'indicador', 'periodo', 'fecha', 'territorio', 'valor', 'provisional', 'nota'])
    for indicador in IndicadorObservatorio.objects.filter(unidad=unidad).order_by('orden', 'nombre'):
        escritor.writerow([indicador.codigo, indicador.nombre, '', '', indicador.territorio_principal, '', '', ''])
    return respuesta
