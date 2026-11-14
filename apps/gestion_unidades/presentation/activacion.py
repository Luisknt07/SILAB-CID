"""Activación independiente de áreas y recursos: existencia y disponibilidad son distintas."""
from django.core.exceptions import ValidationError



def desactivar_area(espacio):
    """Ocultar un área no cambia la existencia física de sus recursos."""
    anotado = dict(espacio.desactivados_con_el_area or {})
    anotado['reservable'] = espacio.reservable
    espacio.activo, espacio.reservable = False, False
    espacio.desactivados_con_el_area = anotado
    espacio.save(update_fields=['activo', 'reservable', 'desactivados_con_el_area'])
    return 'Espacio desactivado; las existencias se administran en cada recurso'


def activar_area(espacio):
    """Habilitar un área no convierte sus referencias en existencias."""
    espacio.activo = True
    espacio.reservable = (espacio.desactivados_con_el_area or {}).get('reservable', True)
    espacio.save(update_fields=['activo', 'reservable'])
    return 'Espacio reactivado; los recursos conservan su existencia registrada'


def alternar_area(espacio):
    return desactivar_area(espacio) if espacio.activo else activar_area(espacio)


def alternar_equipo(equipo):
    if equipo.fecha_baja:
        raise ValidationError('El equipo tiene un retiro operativo registrado. Revisa su ciclo de vida antes de reactivarlo.')
    equipo.activa = not equipo.activa
    equipo.full_clean()
    equipo.save(update_fields=['activa', 'fecha_actualizacion'])
    return 'Equipo reactivado' if equipo.activa else 'Equipo desactivado'


def alternar_software(programa):
    programa.activo = not programa.activo
    programa.full_clean()
    programa.save(update_fields=['activo'])
    return 'Software reactivado' if programa.activo else 'Software desactivado'


def alternar_insumo(insumo):
    insumo.activo = not insumo.activo
    insumo.visible_en_reservas = insumo.activo
    insumo.full_clean()
    insumo.save(update_fields=['activo', 'visible_en_reservas', 'fecha_actualizacion'])
    return 'Insumo reactivado' if insumo.activo else 'Insumo desactivado'
