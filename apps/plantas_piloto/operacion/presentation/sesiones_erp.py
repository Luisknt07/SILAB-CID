"""Quién ve y quién opera cada sesión del ERP de una planta.

Sin sesión se opera la producción real, con los permisos de la unidad. En una
sesión de práctica o individual operan quienes participan mientras está abierta;
el personal de la planta la ve y la acompaña. La demostrativa la ve cualquiera
con cuenta y la opera el personal con permiso de producción.
"""
from django.core.exceptions import PermissionDenied
from django.http import Http404

from apps.plantas_piloto.operacion.models.erp import SesionERP

from apps.gestion_unidades.presentation.permisos import permisos_operativos_unidad, puede_gestionar_unidad, puede_operar_modulo_unidad

# Lo que se opera dentro de una sesión: la cadena productiva, no los datos maestros.
OPERACIONES_EN_SESION = frozenset({
    'plan_ventas', 'linea_plan_ventas', 'plan_maestro', 'linea_plan', 'pedido_abastecimiento',
    'entrega_pedido', 'orden_compra', 'orden_produccion', 'lote_producto', 'movimiento_producto',
    'no_conformidad', 'accion_correctiva',
})


def es_docente(usuario):
    perfil = getattr(usuario, 'profile', None)
    return getattr(perfil, 'tipo_usuario', '') == 'docente'


def puede_ver_sesion(usuario, sesion):
    return (
        sesion.participa(usuario)
        or puede_gestionar_unidad(usuario, sesion.unidad)
        or sesion.tipo == 'demostrativa'
    )


def puede_operar_sesion(usuario, sesion):
    if not sesion.abierta:
        return False
    con_permiso = bool(permisos_operativos_unidad(usuario, sesion.unidad).get('produccion'))
    if sesion.tipo == 'demostrativa':
        return con_permiso
    return sesion.participa(usuario) or con_permiso


def puede_operar_en(usuario, unidad, sesion, modulo='produccion'):
    """Opera un registro de la cadena: en su sesión, quien participa; sin sesión, el permiso de la unidad."""
    if sesion is not None:
        return puede_operar_sesion(usuario, sesion)
    return puede_operar_modulo_unidad(usuario, unidad, modulo)


def sesion_pedida(request, unidad, codigo):
    """La sesión con ese código en la planta, si quien pide puede verla."""
    if not codigo:
        return None
    sesion = SesionERP.objects.filter(unidad=unidad, codigo=codigo).select_related('responsable').first()
    if sesion is None:
        raise Http404('Esa sesión no existe en esta planta.')
    if not puede_ver_sesion(request.user, sesion):
        raise PermissionDenied('No participas en esa sesión.')
    return sesion


def sesion_para_operar(request, unidad):
    """La sesión en la que se registra una operación; sin ella, la producción real."""
    sesion = sesion_pedida(request, unidad, (request.POST.get('sesion_erp') or '').strip())
    if sesion is not None and not puede_operar_sesion(request.user, sesion):
        raise PermissionDenied('La sesión está cerrada o no participas en ella.')
    return sesion


def sesion_de(request):
    """La sesión que la consola dejó en la petición al validar la operación."""
    return getattr(request, 'sesion_erp', None)


def exigir_misma_sesion(sesion_id, request):
    """Un registro de otra sesión, o de la producción real, no se toca desde esta."""
    actual = sesion_de(request)
    if sesion_id != (actual.pk if actual is not None else None):
        raise Http404('Ese registro pertenece a otra sesión del ERP.')


def puede_consultar_en(usuario, unidad, sesion):
    """Consulta una hoja de la cadena: la de una sesión, quien la ve; la real, quien opera la producción."""
    if sesion is not None:
        return puede_ver_sesion(usuario, sesion)
    return puede_operar_modulo_unidad(usuario, unidad, 'produccion')
