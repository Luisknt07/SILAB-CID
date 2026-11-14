"""El ERP de la planta: su pestaña, sus sesiones y quién opera en cada una.

La producción real la opera el personal de la planta con su permiso. Docentes y
estudiantes operan en sesiones: el docente abre una para su práctica y dicta la
clave; cada estudiante puede abrir la suya para practicar. Lo de una sesión no
toca la producción real ni se ve desde otra. Esta vista arma solo lo que el ERP
pinta, así un estudiante entra sin permisos sobre la unidad.
"""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.reservas.models.reservas import Reserva
from apps.plantas_piloto.operacion.models.erp import SesionERP
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

from apps.plantas_piloto.operacion.presentation.calidad import contexto_calidad, seccion_calidad
from apps.plantas_piloto.operacion.presentation.gestion_produccion import contexto_produccion, seccion_produccion
from apps.gestion_unidades.presentation.permisos import MODULOS_OPERATIVOS, permisos_operativos_unidad, puede_gestionar_unidad
from apps.plantas_piloto.operacion.presentation.planificacion import contexto_planificacion, seccion_planificacion
from apps.plantas_piloto.operacion.presentation.planta_operativa import NAVEGACION_ERP, mapa_de_la_planta
from apps.plantas_piloto.operacion.presentation.sesiones_erp import es_docente, puede_operar_sesion, sesion_pedida


def sesiones_visibles(usuario, unidad):
    base = SesionERP.objects.filter(unidad=unidad).select_related('responsable', 'reserva').annotate(
        participantes=Count('miembros', distinct=True),
        ordenes=Count('ordenes_produccion', distinct=True),
    )
    if puede_gestionar_unidad(usuario, unidad):
        return list(base[:60])
    return list(base.filter(
        Q(responsable=usuario) | Q(miembros=usuario) | Q(tipo='demostrativa')
    ).distinct()[:60])


def _seccion_sesiones(sesiones):
    abiertas = sum(sesion.abierta for sesion in sesiones)
    return {
        'clave': 'sesiones',
        'titulo': 'Sesiones de práctica',
        'descripcion': 'Cada práctica opera en su sesión: nada de lo que registra toca la producción real.',
        'icono': 'iconsminds-student-male-female',
        'dato': f'{abiertas} abierta{"s" if abiertas != 1 else ""}',
        'etiqueta': f'{len(sesiones)} en total',
        'habilitada': True,
    }


def _contexto_de_recursos(unidad):
    """Lo que los formularios de producción ofrecen: líneas, equipos, software y responsables."""
    equipos = list(
        UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad), activa=True)
        .select_related('equipo').distinct().order_by('equipo__nombre', 'codigo_unidad')
    )
    return {
        'equipos': equipos,
        'catalogos_equipos_unidad': sorted(
            {equipo.equipo for equipo in equipos}, key=lambda item: (item.nombre.lower(), item.codigo.lower()),
        ),
        'espacios': list(EspacioReservable.objects.filter(unidad=unidad, activo=True).order_by('orden', 'nombre')),
        'software': list(SoftwareDisponible.objects.filter(unidad=unidad, activo=True).order_by('nombre')),
        'responsables': list(
            ResponsableUnidad.objects.filter(unidad=unidad, activo=True).select_related('usuario')
            .order_by('orden', 'nombre')
        ),
    }


@login_required
def erp_planta_view(request, slug):
    """El ERP de la planta, en la producción real o en una sesión de práctica."""
    unidad = get_object_or_404(Unidad, slug=slug)
    configuracion = ConfiguracionOperativaUnidad.objects.filter(unidad=unidad, registra_produccion=True).first()
    if configuracion is None:
        raise Http404('Esta unidad no produce: no tiene ERP.')
    personal = puede_gestionar_unidad(request.user, unidad)
    sesion = sesion_pedida(request, unidad, (request.GET.get('sesion') or '').strip())
    permisos = permisos_operativos_unidad(request.user, unidad) if personal else dict.fromkeys(MODULOS_OPERATIVOS, False)
    if sesion is not None:
        permisos = {**permisos, 'produccion': puede_operar_sesion(request.user, sesion)}
    # Sin sesión, quien no es personal de la planta solo ve sus sesiones: la producción real no es suya.
    cadena = sesion is not None or personal
    sesiones = sesiones_visibles(request.user, unidad)
    secciones = [_seccion_sesiones(sesiones)]
    contextos = {}
    if cadena:
        contextos.update(contexto_produccion(unidad, permisos, configuracion, sesion))
        contextos.update(contexto_calidad(unidad, permisos, configuracion, sesion))
        contextos.update(contexto_planificacion(unidad, permisos, configuracion, sesion))
        secciones += [
            seccion_planificacion(contextos), seccion_produccion(contextos), seccion_calidad(contextos),
        ]
        if sesion is None:
            secciones.append({
                'clave': 'supervision', 'titulo': 'Supervisión',
                'descripcion': 'Sinóptico, variables, alarmas, tendencias e historial de la planta.',
                'icono': 'iconsminds-monitor-analytics', 'dato': 'Estructura lista',
                'etiqueta': 'sin señales conectadas', 'habilitada': True,
            })
        secciones.insert(0, {
            'clave': 'mapa', 'titulo': 'Mapa del ERP',
            'descripcion': 'Los módulos de la cadena productiva y su flujo, del plan a la venta.',
            'icono': 'iconsminds-network', 'dato': 'Cadena productiva', 'etiqueta': 'módulos y flujo',
            'habilitada': True,
        })
    por_clave = {seccion['clave']: seccion for seccion in secciones}
    navegacion = [
        {**por_clave[clave], 'titulo': titulo, 'grupo': grupo}
        for clave, titulo, grupo in NAVEGACION_ERP if clave in por_clave
    ]
    vistas = {seccion['clave'] for seccion in secciones if seccion['habilitada']}
    vista = request.GET.get('view') or ('mapa' if cadena else 'sesiones')
    if vista not in vistas:
        vista = 'mapa' if cadena else 'sesiones'
    base = reverse('erp_planta', args=[unidad.slug])
    contexto = {
        'unidad': unidad,
        'configuracion_operativa': configuracion,
        'palabras_trabajo_unidad': configuracion.formas_trabajo,
        'superficie': 'erp',
        'es_planta_gestion': True,
        'personal_planta': personal,
        'sesion_erp': sesion,
        'erp_url': f'{base}?sesion={sesion.codigo}' if sesion else base,
        'sesiones_erp': sesiones,
        'puede_abrir_practica': personal or es_docente(request.user),
        'practicas_para_sesion': (
            list(Reserva.objects.filter(
                laboratorio=unidad, usuario=request.user, estado__in=('confirmada', 'en_proceso', 'completada'),
            ).order_by('-fecha')[:20])
            if es_docente(request.user) or personal else []
        ),
        'tipos_sesion': [tipo for tipo in SesionERP.TIPOS if tipo[0] != 'demostrativa'],
        'permisos_operativos': permisos,
        'puede_operar_alguna_funcion': True,
        'rol_operativo': (
            'Personal de la planta' if personal else ('Docente' if es_docente(request.user) else 'Estudiante')
        ),
        'tablero': {'estado': (
            {'tono': 'critical', 'etiqueta': 'Producción real'} if sesion is None
            else {'tono': 'ok', 'etiqueta': sesion.get_tipo_display()}
        )},
        'fecha_seleccionada': timezone.localdate(),
        'secciones_gestion': secciones,
        'secciones_navegacion': navegacion,
        'vista_gestion': vista,
        'mapa_planta': mapa_de_la_planta(unidad, permisos, vistas, sesion) if cadena else None,
        **(_contexto_de_recursos(unidad) if cadena else {}),
        **contextos,
    }
    respuesta = render(request, 'portal/pages/unidades/gestion/panel.html', contexto)
    respuesta['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return respuesta


@login_required
@require_POST
def erp_sesion_accion_view(request, slug):
    """Abrir, unirse o cerrar una sesión del ERP."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not ConfiguracionOperativaUnidad.objects.filter(unidad=unidad, registra_produccion=True).exists():
        raise Http404('Esta unidad no produce: no tiene ERP.')
    accion = (request.POST.get('accion') or '').strip()
    try:
        with transaction.atomic():
            if accion == 'unirse':
                clave = (request.POST.get('clave') or '').strip().upper()
                sesion = SesionERP.objects.filter(unidad=unidad, clave_acceso=clave, estado='abierta').first()
                if sesion is None or sesion.tipo != 'practica':
                    raise ValidationError('No hay una sesión de práctica abierta con esa clave en esta planta.')
                sesion.miembros.add(request.user)
                mensaje = f'Entraste a la sesión {sesion.codigo}.'
            elif accion == 'cerrar':
                sesion = get_object_or_404(SesionERP, unidad=unidad, codigo=request.POST.get('sesion_erp'))
                if not (request.user.pk == sesion.responsable_id or puede_gestionar_unidad(request.user, unidad)):
                    raise PermissionDenied('Solo quien la abrió o el personal de la planta cierra la sesión.')
                sesion.cerrar()
                mensaje = f'Sesión {sesion.codigo} cerrada: queda para revisión.'
            else:
                tipo = (request.POST.get('tipo') or 'individual').strip()
                if tipo not in {'practica', 'individual'}:
                    raise ValidationError('Elige el tipo de sesión.')
                if tipo == 'practica' and not (puede_gestionar_unidad(request.user, unidad) or es_docente(request.user)):
                    raise PermissionDenied('Una sesión de práctica la abre un docente o el personal de la planta.')
                nombre = ' '.join((request.POST.get('nombre') or '').split())[:160]
                if not nombre:
                    raise ValidationError('Ponle un nombre a la sesión.')
                reserva = None
                if tipo == 'practica' and request.POST.get('reserva_id'):
                    reserva = get_object_or_404(Reserva, pk=request.POST['reserva_id'], laboratorio=unidad)
                sesion = SesionERP.objects.create(
                    unidad=unidad, nombre=nombre, tipo=tipo, responsable=request.user, reserva=reserva,
                    observaciones=(request.POST.get('observaciones') or '').strip()[:2000],
                )
                sesion.tomar_foto_del_inventario()
                mensaje = (f'Sesión {sesion.codigo} abierta; clave para tus estudiantes: {sesion.clave_acceso}.'
                           if tipo == 'practica' else f'Sesión {sesion.codigo} abierta.')
    except ValidationError as error:
        return JsonResponse({'success': False, 'error': ' '.join(error.messages)}, status=400)
    destino = reverse('erp_planta', args=[unidad.slug]) + (
        '?view=sesiones' if accion == 'cerrar' else f'?sesion={sesion.codigo}'
    )
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('respuesta') == 'json':
        return JsonResponse({'success': True, 'message': mensaje, 'url': destino, 'registro': {'id': sesion.pk}})
    return redirect(destino)
