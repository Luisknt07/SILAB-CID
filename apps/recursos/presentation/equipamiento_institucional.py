"""El equipamiento de toda la Universidad por familia de producto: cuántos hay, dónde están y cuánto se usan.

Sirve para dirigir las compras: antes de adquirir más visores de realidad virtual se ve que hay 10 en
Realidad Extendida, 5 en FabLab y 2 en Logística, cuántas horas se usó cada uno en el último año y si
alguna unidad los tiene casi sin uso mientras otra los necesita. Las familias agrupan el mismo producto
aunque cada unidad lo nombre a su manera (FamiliaEquipo, asignada a cada tipo de equipo).
"""
import csv
from collections import OrderedDict
from datetime import timedelta

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from apps.recursos.models.equipos import FamiliaEquipo
from apps.recursos.models.unidades import UnidadEquipo

from apps.recursos.presentation.equipo_publico import imagen_de
from apps.recursos.presentation.uso_equipos import MUCHO_USO_HORAS, politica_uso, uso_de_equipos

SIN_FAMILIA = 'sin-familia'


def uso_por_codigo(desde):
    """Horas y sesiones de cada equipo (por su código del sistema) en las reservas atendidas desde la fecha."""
    uso = uso_de_equipos(desde)
    return ({codigo: fila['horas'] for codigo, fila in uso.items()},
            {codigo: fila['sesiones'] for codigo, fila in uso.items()})


def diagnostico(total, horas, sesiones, minimo=None):
    if not sesiones:
        return 'sin_uso', 'Sin uso acreditado · verificar registros'
    por_equipo = horas / max(1, total)
    if minimo is not None and por_equipo < minimo:
        return 'subutilizada', 'Poco uso acreditado · revisar causas'
    if por_equipo > MUCHO_USO_HORAS:
        return 'demandada', 'Muy demandada'
    return 'equilibrada', 'Uso equilibrado'


def _equipos(dependencia=''):
    consulta = (UnidadEquipo.objects.filter(activa=True).filter(Q(laboratorio__activo=True) | Q(laboratorios__activo=True))
                .select_related('equipo__familia', 'laboratorio').prefetch_related('espacios_asociados', 'laboratorios').distinct())
    if dependencia:
        consulta = consulta.filter(Q(laboratorio__dependencia=dependencia) | Q(laboratorios__dependencia=dependencia)).distinct()
    return consulta


def _unidad_actual(equipo):
    return equipo.laboratorio or next((u for u in equipo.laboratorios.all() if u.activo), None)


def familias(dependencia='', busqueda=''):
    """Cada familia con sus equipos repartidos por unidad, su uso del último año y qué conviene hacer."""
    hoy = timezone.localdate()
    horas, sesiones = uso_por_codigo(hoy - timedelta(days=365))
    minimo = politica_uso()['horas_minimas_anuales']
    grupos = OrderedDict()
    for equipo in _equipos(dependencia).order_by('equipo__familia__nombre', 'laboratorio__nombre'):
        unidad_actual = _unidad_actual(equipo)
        familia = equipo.equipo.familia
        clave = familia.slug if familia else SIN_FAMILIA
        grupo = grupos.setdefault(clave, {
            'familia': familia, 'clave': clave,
            'nombre': familia.nombre if familia else 'Sin familia asignada',
            'grupo': familia.grupo if familia else '', 'icono': (familia.icono if familia else '') or 'fas fa-cogs',
            'imagen': '', 'equipos': [], 'por_unidad': OrderedDict(),
        })
        grupo['equipos'].append(equipo)
        if not grupo['imagen']:
            grupo['imagen'] = imagen_de(equipo.equipo)[0]
        unidad = grupo['por_unidad'].setdefault(unidad_actual.pk, {
            'unidad': unidad_actual, 'total': 0, 'disponibles': 0, 'horas': 0.0, 'sesiones': 0})
        unidad['total'] += 1
        unidad['disponibles'] += equipo.estado_unidad == 'disponible'
        unidad['horas'] += horas.get(equipo.codigo_unidad, 0.0)
        unidad['sesiones'] += sesiones.get(equipo.codigo_unidad, 0)
    resultado = []
    for grupo in grupos.values():
        if busqueda and busqueda.lower() not in grupo['nombre'].lower():
            continue
        equipos = grupo['equipos']
        total = len(equipos)
        horas_grupo = sum(unidad['horas'] for unidad in grupo['por_unidad'].values())
        sesiones_grupo = sum(unidad['sesiones'] for unidad in grupo['por_unidad'].values())
        estado, etiqueta = diagnostico(total, horas_grupo, sesiones_grupo, minimo)
        unidades = sorted(grupo['por_unidad'].values(), key=lambda unidad: -unidad['total'])
        for unidad in unidades:
            unidad['horas_por_equipo'] = round(unidad['horas'] / max(1, unidad['total']), 1)
            unidad['estado'] = diagnostico(unidad['total'], unidad['horas'], unidad['sesiones'], minimo)[0]
        resultado.append({
            **grupo,
            'total': total,
            'disponibles': sum(1 for equipo in equipos if equipo.estado_unidad == 'disponible'),
            'fuera_de_servicio': sum(1 for equipo in equipos if equipo.estado_unidad in ('mantenimiento', 'dañado')),
            'sin_codigo_bien': sum(1 for equipo in equipos if not equipo.codigo_bien),
            'vida_cumplida': sum(1 for equipo in equipos if equipo.fin_vida_util and equipo.fin_vida_util <= hoy),
            'horas': round(horas_grupo, 1),
            'sesiones': sesiones_grupo,
            'horas_por_equipo': round(horas_grupo / max(1, total), 1),
            'estado': estado,
            'etiqueta': etiqueta,
            'unidades': unidades,
            'recomendacion': recomendacion(unidades),
            'url': reverse('familia_equipo_institucional', args=[grupo['clave']]),
        })
    resultado.sort(key=lambda familia: (-len(familia['unidades']), -familia['total'], familia['nombre']))
    return resultado


def recomendacion(unidades):
    """Antes de comprar: si una unidad tiene equipos casi sin uso y otra los usa mucho, se pueden compartir."""
    ociosas = [unidad for unidad in unidades if unidad['total'] >= 2 and unidad['estado'] in ('sin_uso', 'subutilizada')]
    activas = [unidad for unidad in unidades if unidad['estado'] == 'demandada']
    if ociosas and activas:
        return (f"{ociosas[0]['unidad'].nombre} tiene {ociosas[0]['total']} con poco uso acreditado; "
                f"{activas[0]['unidad'].nombre} los usa {activas[0]['horas_por_equipo']} h por equipo al año. "
                'Revisa registros, estado y necesidades antes de trasladar o compartir; cualquier movimiento requiere aprobación.')
    if len(unidades) > 1 and all(unidad['estado'] == 'sin_uso' for unidad in unidades):
        # Sin reservas atendidas no hay uso medido: no se juzga, se orienta.
        return (f'Lo tienen {len(unidades)} unidades y aún no hay reservas atendidas con cierre completo que midan su uso: '
                'confirma los registros, su estado y si alguna puede compartirlo antes de decidir compras.')
    if len(unidades) > 1 and all(unidad['estado'] in ('sin_uso', 'subutilizada') for unidad in unidades):
        return 'Varias unidades registran poco uso acreditado. Verifica cierres, disponibilidad y necesidades antes de decidir si conviene compartir o comprar.'
    if activas and not ociosas:
        return 'Muy demandado: si se necesita otro, revisa primero si alguna unidad puede prestarlo.'
    return ''


def _resumen(lista):
    equipos = sum(familia['total'] for familia in lista)
    return {
        'familias': len(lista),
        'equipos': equipos,
        'compartidas': sum(1 for familia in lista if len(familia['unidades']) > 1),
        'subutilizadas': sum(1 for familia in lista if familia['estado'] in ('subutilizada', 'sin_uso')),
        'sin_codigo_bien': sum(familia['sin_codigo_bien'] for familia in lista),
        'vida_cumplida': sum(familia['vida_cumplida'] for familia in lista),
    }


def _csv(nombre, encabezados, filas):
    respuesta = HttpResponse(content_type='text/csv; charset=utf-8')
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
    respuesta.write('﻿')
    escritor = csv.writer(respuesta, delimiter=';')
    escritor.writerow(encabezados)
    escritor.writerows(filas)
    return respuesta


@login_required
@permission_required('recursos.view_unidadequipo', raise_exception=True)
def equipamiento_institucional_view(request):
    dependencia = request.GET.get('dependencia', '')
    busqueda = (request.GET.get('q') or '').strip()
    lista = familias(dependencia, busqueda)
    if request.GET.get('formato') == 'csv':
        return _csv('equipamiento-institucional.csv',
                    ('Familia', 'Grupo', 'Equipos', 'Disponibles', 'Unidades', 'Horas (12 meses)', 'Horas por equipo',
                     'Diagnóstico', 'Sin código de bodega', 'Vida útil cumplida'),
                    [(f['nombre'], f['grupo'], f['total'], f['disponibles'],
                      ' · '.join(f"{u['unidad'].nombre}: {u['total']}" for u in f['unidades']),
                      f['horas'], f['horas_por_equipo'], f['etiqueta'], f['sin_codigo_bien'], f['vida_cumplida'])
                     for f in lista])
    dependencias = UnidadEquipo._meta.get_field('laboratorio').related_model._meta.get_field('dependencia').choices
    return render(request, 'portal/pages/unidades/institucional/equipamiento.html', {
        'familias': lista,
        'resumen': _resumen(lista),
        'dependencia': dependencia,
        'busqueda': busqueda,
        'dependencias': dependencias,
        'umbrales': (politica_uso()['horas_minimas_anuales'], MUCHO_USO_HORAS),
    })


@login_required
@permission_required('recursos.view_unidadequipo', raise_exception=True)
def familia_equipo_institucional_view(request, clave):
    if clave != SIN_FAMILIA:
        get_object_or_404(FamiliaEquipo, slug=clave)
    familia = next((item for item in familias() if item['clave'] == clave), None)
    if familia is None:
        raise Http404('La familia no tiene equipos activos.')
    hoy = timezone.localdate()
    horas, sesiones = uso_por_codigo(hoy - timedelta(days=365))
    filas = []
    for equipo in sorted(familia['equipos'], key=lambda e: (_unidad_actual(e).nombre, e.codigo_unidad)):
        unidad_actual = _unidad_actual(equipo)
        filas.append({
            'equipo': equipo, 'unidad_actual': unidad_actual,
            'areas': ', '.join(espacio.nombre for espacio in equipo.espacios_asociados.all()),
            'horas': round(horas.get(equipo.codigo_unidad, 0.0), 1),
            'sesiones': sesiones.get(equipo.codigo_unidad, 0),
            'url': reverse('ficha_equipo_publica', args=[unidad_actual.slug, equipo.codigo_unidad]),
        })
    if request.GET.get('formato') == 'csv':
        return _csv(f'familia-{clave}.csv',
                    ('Unidad', 'Área', 'Código del sistema', 'Código del bien', 'Equipo', 'Estado', 'Horas (12 meses)', 'Sesiones'),
                    [(f['unidad_actual'].nombre, f['areas'], f['equipo'].codigo_unidad, f['equipo'].codigo_bien or '',
                      f['equipo'].equipo.nombre, f['equipo'].get_estado_unidad_display(), f['horas'], f['sesiones'])
                     for f in filas])
    return render(request, 'portal/pages/unidades/institucional/familia.html', {
        'familia': familia, 'filas': filas, 'umbrales': (politica_uso()['horas_minimas_anuales'], MUCHO_USO_HORAS),
    })
