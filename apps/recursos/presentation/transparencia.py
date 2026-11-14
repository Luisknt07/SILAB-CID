"""Lectura de uso por activo con alcance de gestión y exportación transparente."""
import csv

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad, unidades_gestionables
from apps.recursos.presentation.traspasos import equipos_asignados, puede_aprobar, transparencia_equipos
from apps.recursos.presentation.uso_equipos import SITUACIONES


def _celda_csv(valor):
    valor = '' if valor is None else str(valor)
    return "'" + valor if valor.lstrip().startswith(('=', '+', '-', '@')) else valor


def transparencia_equipos_view(request):
    """GET sin mutaciones; una lectura no comunica ni inicia un traspaso."""
    global_ = puede_aprobar(request.user)
    if global_:
        unidades = Unidad.objects.filter(activo=True).order_by('nombre')
    else:
        permitidas = [u.pk for u in unidades_gestionables(request.user)
                      if puede_operar_modulo_unidad(request.user, u, 'recursos')]
        unidades = Unidad.objects.filter(pk__in=permitidas).order_by('nombre')
        if not permitidas:
            raise PermissionDenied('La transparencia de equipos corresponde a Dirección o a la gestión de recursos de tu unidad.')
    seleccion = request.GET.get('unidad', '')
    unidad = None
    if seleccion:
        try:
            unidad = unidades.filter(pk=int(seleccion)).first()
        except (ValueError, TypeError):
            return HttpResponseBadRequest('Selecciona una unidad válida.')
        if unidad is None:
            raise PermissionDenied('No tienes acceso a los equipos de esta unidad.')
    equipos = equipos_asignados(unidad)
    if not global_:
        equipos = equipos.filter(Q(laboratorio__in=unidades) | Q(laboratorios__in=unidades)).distinct()
    lectura = transparencia_equipos(equipos=equipos)
    estado = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '').strip()[:200]
    detalle_equipo = request.GET.get('equipo_id', '')
    filas = [f for f in lectura['filas']
             if (not estado or estado == f['lectura']['clave']
                 or estado == 'candidata' and f['redistribucion']['candidata'])
             and (not busqueda or busqueda.casefold() in (f['codigo'] + ' ' + f['nombre']).casefold())]
    if detalle_equipo:
        filas = [f for f in filas if str(f['equipo_id']) == detalle_equipo]
    parametros = request.GET.copy()
    for clave in ('pagina', 'actividad_pagina', 'formato'):
        parametros.pop(clave, None)
    parametros_exportacion = parametros.urlencode()
    if request.GET.get('formato') != 'csv':
        por_pagina = 100 if request.GET.get('por_pagina') == '100' else 50
        pagina = Paginator(filas, por_pagina).get_page(request.GET.get('pagina'))
        filas = pagina.object_list
    else:
        pagina = None
    puede_abrir_reservas = request.user.has_perm('reservas.view_reserva') or request.user.has_perm('reservas.change_reserva')
    for fila in filas:
        fila['ficha_url'] = (reverse('ficha_equipo_publica', args=[fila['unidad'].slug, fila['codigo']])
                             if fila['unidad'] else '')
        fila['alerta_url'] = (reverse('admin:recursos_alertausoequipo_change', args=[fila['alerta'].pk])
                             if fila['alerta'] and request.user.has_perm('recursos.change_alertausoequipo') else '')
        fuentes = fila['lectura']['fuentes']
        fila['total_fuentes'] = len(fuentes)
        fila['actividad_pagina'] = (Paginator(fuentes, 25).get_page(request.GET.get('actividad_pagina'))
                                   if detalle_equipo else None)
        fila['fuentes_vista'] = (fila['actividad_pagina'].object_list if detalle_equipo else fuentes[:10])
        para_equipo = parametros.copy()
        para_equipo['equipo_id'] = str(fila['equipo_id'])
        fila['detalle_url'] = '?' + para_equipo.urlencode()
        for fuente in fila['fuentes_vista']:
            fuente['url'] = (reverse('admin:reservas_reserva_change', args=[fuente['reserva_id']])
                             if puede_abrir_reservas else '')
    if request.GET.get('formato') == 'csv':
        respuesta = HttpResponse(content_type='text/csv; charset=utf-8')
        respuesta['Content-Disposition'] = 'attachment; filename="transparencia-equipos.csv"'
        respuesta.write('\ufeff')
        escritor = csv.writer(respuesta, delimiter=';')
        escritor.writerow(['Unidad principal', 'Código', 'Equipo', 'Áreas', 'Estado operativo', 'Lectura de uso',
            'Horas acreditadas (12 meses)', 'Sesiones', 'Último uso', 'Cierres pendientes', 'Fuentes (reservas)',
            'Comunicación a la unidad', 'Fecha de revisión', 'Plan de uso', 'Revisión de redistribución', 'Corte'])
        for fila in filas:
            alerta, uso = fila['alerta'], fila['lectura']
            escritor.writerow([_celda_csv(v) for v in [fila['unidad'].nombre if fila['unidad'] else 'Asignación compartida',
                fila['codigo'], fila['nombre'], ', '.join(a.nombre for a in fila['areas']),
                fila['equipo'].get_estado_unidad_display(), uso['etiqueta'], uso['horas'], uso['sesiones'],
                uso['ultimo'], ', '.join(str(p) for p in uso['pendientes']),
                ', '.join(str(f['reserva_id']) for f in uso['fuentes']), alerta.notificada_en if alerta else '',
                alerta.revisar_desde if alerta else '', alerta.plan_uso if alerta else '',
                fila['redistribucion']['motivo'], lectura['corte']]])
        return respuesta
    return render(request, 'admin/recursos/unidadequipo/transparencia.html', {
        **admin.site.each_context(request), 'title': 'Transparencia en el uso de equipos',
        'lectura': lectura, 'filas': filas, 'unidades': unidades, 'unidad_seleccionada': str(unidad.pk) if unidad else '',
        'estado': estado, 'busqueda': busqueda, 'estados': SITUACIONES.items(),
        'puede_revisar': global_, 'query_exportacion': parametros_exportacion,
        'pagina': pagina, 'query_paginacion': parametros.urlencode(), 'detalle_equipo': detalle_equipo,
        'query_actividad': parametros.urlencode(),
    })
