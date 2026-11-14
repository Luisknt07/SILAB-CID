"""La propuesta conserva una copia explicable de las referencias que utilizó."""
from apps.documentos.models.referencias_indicadores import ReferenciaIndicadorUnidad


def referencias_para(unidad):
    return [dict(id=r.pk, codigo=r.codigo, nivel=r.nivel_capacidad, valor=r.valor,
        fundamento=r.fundamento, actualizado_en=r.actualizado_en.isoformat(),
        actualizado_por=r.actualizado_por_id) for r in ReferenciaIndicadorUnidad.objects.filter(
            tipo_unidad=unidad.codigo_base, activo=True).order_by('codigo', 'nivel_capacidad')]


def referencia(capacidad, codigo, nivel=''):
    datos = (capacidad or {}).get('referencias_indicadores') or []
    for dato in datos:
        if dato.get('codigo') == codigo and dato.get('nivel', '') == nivel:
            return dato
    return None
