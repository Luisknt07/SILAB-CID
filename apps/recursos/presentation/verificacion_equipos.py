"""La verificación de que cada equipo existe: quien gestiona la unidad lo confirma (o anota que no se localizó).

Mientras se cargan y ordenan los datos, los equipos se toman como existentes. Cuando la institución activa la
exigencia (CITT_EXIGIR_EQUIPOS_VERIFICADOS), el público solo ve los verificados. Siempre, el público ve solo lo
que está en servicio (disponible, en uso o prestado); lo dañado, en mantenimiento, obsoleto o no localizado lo
ve quien gestiona.
"""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad, puede_operar_modulo_unidad


def puede_verificar(usuario, unidad):
    return bool(unidad) and puede_operar_modulo_unidad(usuario, unidad, 'recursos')


def publicos_para(equipos, unidad, usuario):
    """Los equipos que ve este visitante: todos para quien gestiona; para los demás, solo los públicos."""
    if usuario is not None and puede_gestionar_unidad(usuario, unidad):
        return list(equipos)
    return [equipo for equipo in equipos if equipo.es_publico]


def verificar_existencia(equipo, usuario, existe=True, nota=''):
    """Confirma que el equipo existe o anota que no se localizó (pasa a «No localizado»).

    Una referencia que se confirma vuelve a existir: se activa y deja de ser dotación propuesta en la ficha.
    """
    with transaction.atomic():
        equipo.existencia_verificada = existe
        equipo.existencia_verificada_en = timezone.now()
        equipo.existencia_verificada_por = usuario
        equipo.existencia_nota = nota[:240]
        if existe and equipo.estado_unidad == 'no_localizado':
            equipo.estado_unidad = 'disponible'
        elif not existe:
            equipo.estado_unidad = 'no_localizado'
        if existe and not equipo.activa and not equipo.fecha_baja:
            equipo.activa = True
            equipo.elementos_de_ficha.filter(solo_referencia=True).update(solo_referencia=False)
        equipo.save()
        quien = usuario.get_full_name() or usuario.username
        EventoCicloVidaEquipo.objects.create(
            equipo=equipo, unidad=equipo.laboratorio, tipo='verificacion', usuario=usuario,
            descripcion=(f'Existencia confirmada por {quien}.' if existe else f'No se localizó el equipo en la verificación de {quien}.')
                        + (f' {nota}' if nota else ''))
    return equipo


@login_required
@require_POST
def verificar_equipo_view(request, slug, codigo):
    unidad = get_object_or_404(Unidad, slug=slug)
    equipo = UnidadEquipo.objects.filter(laboratorio=unidad, codigo_unidad=codigo).first()
    if equipo is None:
        raise Http404('El equipo no es de esta unidad.')
    if not puede_verificar(request.user, unidad):
        raise PermissionDenied('Solo quien gestiona los recursos de la unidad verifica sus equipos.')
    verificar_existencia(equipo, request.user, existe=request.POST.get('resultado') != 'no_localizado',
                         nota=(request.POST.get('nota') or '').strip())
    if request.headers.get('Accept', '').startswith('application/json'):
        return JsonResponse({'verificado': equipo.existencia_verificada, 'estado': equipo.get_estado_unidad_display()})
    return redirect(reverse('ficha_equipo_publica', args=[slug, equipo.codigo_unidad]) + '#identidad')
