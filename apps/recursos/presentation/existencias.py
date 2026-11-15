"""Qué respalda que un equipo exista y qué describe solo una dotación propuesta.

Un equipo existe cuando algo lo respalda: su existencia se verificó, es un bien patrimonial importado del
reporte de bodega o el responsable declaró la cantidad. Lo demás que describen las fichas de área es
referencia hasta que la unidad lo confirme. Lo usan la conciliación de existencias y la sincronización de
fichas, para que ninguna convierta una descripción en inventario.
"""
import re

from django.db.models import Q


def respaldo(equipo):
    """Por qué consta que el equipo existe («verificada», «patrimonial», «declarada»), o vacío si nada lo respalda."""
    if equipo.existencia_verificada:
        return 'verificada'
    if (equipo.codigo_bien or '').strip() and (equipo.valor_contable is not None or equipo.fecha_ingreso_bodega):
        return 'patrimonial'
    if (equipo.existencia_nota or '').startswith('Cantidad declarada'):
        return 'declarada'
    return ''


def tiene_inventario_patrimonial(unidad):
    """Si ya se importó el reporte de bodega de la unidad: entonces su inventario es ese, no lo que dicen las fichas."""
    from apps.recursos.models.unidades import UnidadEquipo

    return UnidadEquipo.objects.filter(laboratorio=unidad, activa=True).exclude(codigo_bien__isnull=True).exclude(
        codigo_bien='').filter(Q(valor_contable__isnull=False) | Q(fecha_ingreso_bodega__isnull=False)).exists()


def por_verificar(texto):
    return 'por verificar' in (texto or '').lower()


def describe_propuesta(elemento):
    """Si la ficha describe el equipo como algo por adquirir: alta capacidad, «por verificar» o cantidad «0 a 1»."""
    cantidad = re.match(r'\s*(\d+)', elemento.cantidad or '')
    return (elemento.nivel == 'alta' or por_verificar(elemento.nombre)
            or (cantidad is not None and int(cantidad.group(1)) == 0))
