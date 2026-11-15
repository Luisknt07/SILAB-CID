"""Páginas públicas de una unidad que salen de sus registros: software, insumos y asignaturas.

Son las secciones 2.3, 2.4 y 4.2 del mapa de laboratorios (los insumos, también la 2.2 de las plantas). Se abren en el visualizador de
la ficha y muestran solo lo activo; no exponen licencias por usuario ni datos personales.
"""
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin

from django.http import Http404

from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo
from apps.directorio_unidades.models.core import Unidad

from apps.laboratorios.operacion.presentation.actividad_laboratorio import GRUPOS, actividades_de
from apps.gestion_unidades.presentation.conoce import foto_de_portada
from apps.gestion_unidades.presentation.edicion_registro import ediciones_de
from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad
from apps.plantas_piloto.operacion.presentation.secciones_plantas import mapa_de


def _contexto(unidad, clave, usuario=None):
    mapa = mapa_de(unidad)
    numero = mapa.numero(clave) if mapa else ''
    modulo = mapa.modulo_de(numero) if numero else ''
    return {
        'unidad': unidad,
        'seccion': numero,
        'volver_url': f'{unidad.get_absolute_url()}#{modulo}' if modulo else unidad.get_absolute_url(),
        'generado_en': timezone.localtime(),
        'foto_portada': foto_de_portada(unidad),
        'ediciones': ediciones_de(usuario, unidad),
    }


@xframe_options_sameorigin
def software_unidad_view(request, slug):
    """El software y las plataformas disponibles, con su versión, licencias y forma de acceso."""
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    gestor = puede_gestionar_unidad(request.user, unidad)
    software = list(
        unidad.software_disponible.filter(**({} if gestor else {'activo': True}))
        .prefetch_related('equipos_instalados__equipo', 'elementos_de_ficha__ficha__espacio')
        .order_by('tipo_recurso', 'nombre', 'version')
    )
    grupos = []
    gestor = puede_gestionar_unidad(request.user, unidad)
    for programa in software:
        # Las áreas que lo usan (por su ficha publicada; su gestor ve también los borradores) y los equipos activos.
        elementos = [elemento for elemento in programa.elementos_de_ficha.all() if gestor or elemento.ficha.publicada]
        espacios = {elemento.ficha.espacio for elemento in elementos}
        programa.areas = [{'nombre': espacio.nombre, 'url': reverse('area_unidad', args=[unidad.slug, espacio.codigo])}
                          for espacio in sorted(espacios, key=lambda espacio: (espacio.orden, espacio.nombre))]
        licencias = {elemento.licencia for elemento in elementos if elemento.licencia}
        programa.licencia = ', '.join(sorted(licencias))
        por_tipo = {}
        # Un equipo que el público no puede abrir (no disponible o sin verificar) no se enlaza a un visitante.
        for fisica in sorted((fisica for fisica in programa.equipos_instalados.all()
                              if fisica.activa and (gestor or fisica.es_publico)),
                             key=lambda fisica: fisica.codigo_unidad):
            por_tipo.setdefault(fisica.equipo_id, []).append(fisica)
        programa.equipos = [{'nombre': unidades[0].equipo.nombre, 'cantidad': len(unidades),
                             'url': reverse('ficha_equipo_publica', args=[unidad.slug, unidades[0].codigo_unidad])}
                            for unidades in sorted(por_tipo.values(), key=lambda unidades: unidades[0].equipo.nombre)]
        tipo = programa.get_tipo_recurso_display()
        if not grupos or grupos[-1]['nombre'] != tipo:
            grupos.append({'nombre': tipo, 'programas': []})
        grupos[-1]['programas'].append(programa)
    return render(request, 'portal/pages/unidades/aula/software.html', {
        **_contexto(unidad, 'software', request.user),
        'grupos': grupos,
        'total': sum(programa.activo for programa in software),
        'referencias_inactivas': sum(not programa.activo for programa in software),
    })


@xframe_options_sameorigin
def insumos_unidad_view(request, slug):
    """Los insumos y materiales del inventario, por clase, con su presentación, el área donde se guardan,
    los equipos que los usan y si ya tienen stock; el mismo registro que usan reservas y reportes."""
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    gestor = puede_gestionar_unidad(request.user, unidad)
    insumos = list(Consumible.objects.filter(unidad=unidad, **({} if gestor else {'activo': True})).order_by('clasificacion', 'nombre'))
    equipos = {}
    for relacion in ConsumiblePorEquipo.objects.filter(consumible__in=insumos).select_related('equipo'):
        equipos.setdefault(relacion.consumible_id, set()).add(relacion.equipo.nombre)
    clases = dict(Consumible.CLASIFICACIONES)
    grupos = []
    for insumo in insumos:
        insumo.equipos = sorted(equipos.get(insumo.pk, ()))
        if not grupos or grupos[-1]['clave'] != insumo.clasificacion:
            grupos.append({'clave': insumo.clasificacion, 'nombre': clases.get(insumo.clasificacion, insumo.clasificacion),
                           'detalle': Consumible.CLASIFICACION_DETALLE.get(insumo.clasificacion, ('', ''))[1],
                           'insumos': []})
        grupos[-1]['insumos'].append(insumo)
    mapa = mapa_de(unidad)
    clave = 'materiales_insumos' if mapa and mapa.tipo == 'plantas_piloto' else 'materiales'
    return render(request, 'portal/pages/unidades/aula/insumos.html', {
        **_contexto(unidad, clave, request.user),
        'grupos': grupos,
        'total': sum(insumo.activo for insumo in insumos),
        'referencias_inactivas': sum(not insumo.activo for insumo in insumos),
        'con_stock': sum(1 for insumo in insumos if insumo.activo and insumo.stock_total > 0),
    })


@xframe_options_sameorigin
def asignaturas_unidad_view(request, slug):
    """Las asignaturas y carreras que practican en la unidad, por carrera."""
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    asignaturas = list(
        unidad.asignaturas.filter(activa=True).select_related('periodo').order_by('carrera', 'semestre', 'nombre')
    )
    carreras = []
    for asignatura in asignaturas:
        carrera = asignatura.carrera or 'Otras carreras'
        if not carreras or carreras[-1]['nombre'] != carrera:
            carreras.append({'nombre': carrera, 'asignaturas': []})
        carreras[-1]['asignaturas'].append(asignatura)
    return render(request, 'portal/pages/unidades/aula/asignaturas.html', {
        **_contexto(unidad, 'asignaturas', request.user),
        'carreras': carreras,
        'total': len(asignaturas),
    })


# El icono de cada sección de actividad en las tarjetas del visualizador.
ICONOS_DE_GRUPO = {
    'proyectos_formativos': 'fas fa-lightbulb',
    'colaboracion_centros': 'fas fa-handshake',
    'vinculacion': 'fas fa-hands-helping',
}


@xframe_options_sameorigin
def proyectos_unidad_view(request, slug, clave):
    """Proyectos formativos, colaboración con centros de I+D o vinculación, según las reservas aprobadas."""
    if clave not in GRUPOS:
        raise Http404('Sección desconocida')
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    filas = actividades_de(unidad)[clave]
    return render(request, 'portal/pages/unidades/aula/proyectos.html', {
        **_contexto(unidad, clave, request.user),
        'titulo_seccion': GRUPOS[clave][0],
        'icono': ICONOS_DE_GRUPO[clave],
        'actividades': filas,
        'total_sesiones': sum(fila['sesiones'] for fila in filas),
        'total_horas': round(sum(fila['horas'] for fila in filas), 1),
    })
