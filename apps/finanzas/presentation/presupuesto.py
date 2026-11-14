"""Lo que el sistema ve que la unidad debería comprar, y por qué.

La unidad planifica su presupuesto semestre a semestre y sus compras año a
año. El sistema identifica necesidades a partir del inventario registrado:
qué equipos cumplieron su vida útil, cuáles se dieron de baja sin reemplazo,
cuáles críticos están fuera de servicio y qué insumos se agotaron: eso es lo
que sugiere, con su motivo, para que la unidad lo justifique o lo descarte.
"""

from datetime import timedelta

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.unidades import UnidadEquipo

MOTIVOS_SIN_REEMPLAZO = ('obsolescencia', 'vida_util', 'dano_irreparable', 'perdida')


def _fin_de_vida(equipo):
    """Cuándo termina la vida útil de referencia, si se sabe."""
    return equipo.fin_vida_util


def sugerencias_de_compra(unidad, hoy=None, *, hasta=None):
    """Necesidades para revisar, sin crear compras ni declarar bajas.

    Cada activo aparece una vez, con todos sus motivos. Un daño pide primero
    diagnóstico; la antigüedad por sí sola tampoco demuestra inutilidad.
    El importe del inventario sólo es una referencia, nunca una cotización.
    """
    hoy = hoy or timezone.localdate()
    horizonte = max(hoy, hasta or hoy + timedelta(days=365))
    filas = []
    equipos = list(
        UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad))
        .select_related('equipo').distinct()
    )
    por_id = {e.pk: e for e in equipos}
    for e in equipos:
        nombre = f'{e.equipo.nombre} ({e.codigo_unidad})' if e.equipo_id else e.codigo_unidad
        referencia = e.valor_referencial
        motivos, prioridad, categoria = [], 'media', 'equipos'
        accion = 'Evaluar renovación'
        if e.fecha_baja:
            if e.fecha_baja > hoy or e.motivo_baja not in MOTIVOS_SIN_REEMPLAZO:
                continue
            # El sucesor se analiza por su propia ficha; no se piden dos
            # reposiciones por una misma cadena histórica.
            sucesor, visitados = e, {e.pk}
            while sucesor.reemplazado_por_id in por_id and sucesor.reemplazado_por_id not in visitados:
                sucesor = por_id[sucesor.reemplazado_por_id]
                visitados.add(sucesor.pk)
            if sucesor.pk != e.pk and (sucesor.activa or sucesor.fecha_baja) and not sucesor.reemplazado_por_id:
                continue
            if not e.reemplazado_por_id:
                motivos.append(f'Dado de baja el {e.fecha_baja:%d/%m/%Y} ({e.get_motivo_baja_display()}) '
                               'y sin reemplazo registrado.')
            else:
                motivos.append('El reemplazo registrado no cierra una cadena válida de activos de esta unidad. '
                               'Revisa la sustitución antes de presupuestar otra compra.')
            prioridad, accion = 'alta', 'Revisar reposición pendiente'
        elif not e.activa:
            continue
        else:
            fin = _fin_de_vida(e)
            if e.estado_unidad == 'obsoleto':
                motivos.append('Obsolescencia técnica registrada: documentar la necesidad y las prestaciones del sustituto.')
            if fin and fin <= hoy:
                motivos.append(f'Cumplió su vida útil de referencia ({e.vida_util_efectiva} años) el {fin:%d/%m/%Y}. '
                               'Comprobar funcionalidad antes de decidir su renovación.')
            elif fin and fin <= horizonte:
                motivos.append(f'Su vida útil de referencia termina el {fin:%d/%m/%Y}: conviene prever el reemplazo.')
                prioridad = 'media' if e.criticidad == 'critico' else 'baja'
            if e.estado_unidad in ('dañado', 'no_disponible'):
                motivos.append(f'Estado registrado: {e.get_estado_unidad_display()}. '
                               'Comparar reparación, garantía y reposición con un diagnóstico técnico.')
                accion = 'Evaluar reparación o renovación'
                if not fin or fin > hoy:
                    categoria = 'mantenimiento' if e.estado_unidad != 'obsoleto' else 'equipos'
                prioridad = 'alta' if e.criticidad == 'critico' else 'media'
            elif motivos and e.criticidad == 'critico' and (e.estado_unidad == 'obsoleto' or fin and fin <= hoy):
                prioridad = 'alta'
        if motivos:
            filas.append(dict(clave=f'equipo:{e.pk}', equipo_id=e.pk, categoria=categoria, item=nombre,
                codigo_equipo=e.codigo_unidad,
                requiere_atencion=(e.criticidad == 'critico' and
                    (bool(e.fecha_baja) or e.estado_unidad in ('dañado', 'no_disponible', 'obsoleto'))),
                motivo=' '.join(motivos), prioridad=prioridad, referencia=referencia, accion=accion,
                url_equipo=reverse('ficha_equipo_unidad', args=[unidad.slug, e.pk])))
    for c in Consumible.objects.filter(unidad=unidad, activo=True):
        estado = c.estado_stock
        if estado in ('agotado', 'critico'):
            filas.append({'clave': f'insumo:{c.pk}', 'equipo_id': None, 'url_equipo': '',
                          'accion': 'Revisar reposición de existencias',
                          'categoria': 'insumos', 'item': c.nombre, 'referencia': None,
                          'prioridad': 'alta' if estado == 'agotado' else 'media',
                          'motivo': 'Existencia agotada.' if estado == 'agotado'
                                    else 'Por debajo del stock de seguridad.'})
    orden = {'alta': 0, 'media': 1, 'baja': 2}
    return sorted(filas, key=lambda f: (orden[f['prioridad']], f['categoria'], f['item']))


def bloque_de_sugerencias(unidad, hoy=None, *, hasta=None):
    """La tabla «Lo que el sistema sugiere», lista para el editor y el PDF."""
    filas = sugerencias_de_compra(unidad, hoy, hasta=hasta)
    if not filas:
        return {'tipo': 'vacio', 'titulo': 'Lo que el sistema sugiere',
                'texto': 'No se detectan necesidades con los datos registrados. Esto no certifica que el inventario '
                         'esté completo: confirma la capacidad y justifica si no se requieren compras.'}
    etiquetas = {'equipos': 'Equipos', 'insumos': 'Insumos y materiales', 'mantenimiento': 'Mantenimiento'}
    prioridades = {'alta': 'Alta', 'media': 'Media', 'baja': 'Baja'}
    return {
        'tipo': 'tabla', 'titulo': 'Lo que el sistema sugiere',
        'cabecera': ['Categoría', 'Ítem', 'Por qué', 'Prioridad', 'Valor de referencia (USD)'],
        'filas': [[etiquetas[f['categoria']], f['item'], f['motivo'], prioridades[f['prioridad']],
                   f'{f["referencia"]:,.2f}' if f['referencia'] else '—'] for f in filas],
    }
