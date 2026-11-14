"""Directorio administrativo según asignaciones reales, sin modificar permisos."""
from collections import OrderedDict

from apps.core.presentation.tipologias import nombre_tipologia
from apps.directorio_unidades.models.core import Unidad


def agrupar_cuentas(cuentas, *, incluir_vacias=True):
    unidades = OrderedDict((u.pk, {'unidad': u, 'usuarios': []})
                           for u in Unidad.objects.order_by('dependencia', 'nombre'))
    sin_unidad = []
    for cuenta in cuentas.order_by('last_name', 'first_name', 'username'):
        roles = {}
        for unidad in cuenta.unidades_administradas.all():
            roles.setdefault(unidad.pk, []).append('Administrador principal')
        for responsable in cuenta.responsabilidades_en_unidades.all():
            roles.setdefault(responsable.unidad_id, []).append(
                responsable.get_rol_display() + ('' if responsable.activo else ' (delegación inactiva)'))
        for unidad_id, etiquetas in roles.items():
            if unidad_id in unidades:
                unidades[unidad_id]['usuarios'].append({'cuenta': cuenta, 'rol': ' · '.join(etiquetas)})
        if not roles:
            sin_unidad.append({'cuenta': cuenta, 'rol': 'Superadministrador' if cuenta.is_superuser
                              else 'Acceso institucional' if cuenta.is_staff else 'Usuario solicitante'})
    grupos = OrderedDict()
    for fila in unidades.values():
        if not fila['usuarios'] and not incluir_vacias:
            continue
        codigo = fila['unidad'].dependencia
        grupo = grupos.setdefault(codigo, {'nombre': nombre_tipologia(codigo, plural=True), 'unidades': []})
        grupo['unidades'].append(fila)
    return list(grupos.values()), sin_unidad
