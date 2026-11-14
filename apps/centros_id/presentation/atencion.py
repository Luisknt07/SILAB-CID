"""Expediente privado de la solicitud y acciones explícitas de su titular o de gestión."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import router, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods

from apps.centros_id.identidades import identidad_de

from .views import _centro, _contenidos
from .secciones import _base


@login_required
@require_http_methods(['GET', 'POST'])
@xframe_options_sameorigin
def solicitud_view(request, slug, pk):
    from apps.centros_id.formularios import SeguimientoForm
    from apps.centros_id.models import RegistroSolicitud

    centro = _centro(slug)
    gestor = centro.puede_gestionar(request.user)
    consulta = centro.solicitudes.all()
    if not gestor:
        consulta = consulta.filter(usuario_id=request.user.pk)
    solicitud = get_object_or_404(consulta.select_related('responsable_atencion', 'zona', 'equipo', 'supervisor'), pk=pk)
    formulario = SeguimientoForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and formulario.is_valid():
        with transaction.atomic(using=router.db_for_write(type(solicitud))):
            solicitud = consulta.select_for_update().get(pk=pk)
            accion = request.POST.get('accion', 'informacion')
            detalle = formulario.cleaned_data['detalle']
            if accion == 'cancelar':
                if solicitud.estado == 'cancelada':
                    return redirect('solicitud_detalle_centro_id', slug=slug, pk=pk)
                if not solicitud.puede_retirar and not (gestor and solicitud.estado == 'ejecucion'):
                    formulario.add_error(None, 'Este estado requiere gestionar el cierre con el centro.')
                else:
                    solicitud.avanzar('cancelada')
                    solicitud.save(actor=request.user, motivo=detalle)
                    messages.success(request, 'La solicitud quedó cancelada; conservamos su historial.')
            elif accion == 'informacion':
                RegistroSolicitud.objects.create(solicitud=solicitud, autor=identidad_de(request.user),
                    estado_anterior=solicitud.estado, estado_nuevo=solicitud.estado, detalle=detalle)
                messages.success(request, 'La información quedó registrada en el expediente.')
            else:
                formulario.add_error(None, 'Acción no reconocida.')
        if not formulario.errors:
            return redirect('solicitud_detalle_centro_id', slug=slug, pk=pk)
    c = _contenidos(centro, request.user)
    contexto = _base(request, centro, c, 'solicitar')
    from .paginacion import paginar
    paginacion_historial = paginar(solicitud.historial.select_related('solicitud').order_by('fecha', 'pk'),
                                  request, parametro='pagina_historial', tamanio=40, fragmento='#historial')
    paginacion_sesiones = paginar(solicitud.sesiones.select_related('responsable').order_by('inicio', 'pk'),
                                 request, parametro='pagina_sesiones', fragmento='#sesiones')
    paginacion_tareas = paginar(solicitud.tareas.order_by('plazo', 'pk'),
                               request, parametro='pagina_tareas', fragmento='#compromisos')
    contexto.update(solicitud=solicitud, seguimiento_form=formulario, historial=paginacion_historial['pagina'],
                    sesiones=paginacion_sesiones['pagina'], tareas=paginacion_tareas['pagina'],
                    paginacion_historial=paginacion_historial, paginacion_sesiones=paginacion_sesiones,
                    paginacion_tareas=paginacion_tareas,
                    ahora=timezone.now())
    return render(request, 'centros_id/visor/solicitud_detalle.html', contexto)
