"""Procesos, métodos y productos de un laboratorio: la pestaña 3 de su ficha.

Un laboratorio no produce por lotes, pero sí tiene procesos: imprimir una pieza, cortar
una placa, digitalizar un objeto. Se guardan en las mismas tablas que los procesos de
una planta (proceso, etapas, insumos, software y salidas) y aquí se muestran sin nada
de producción: ni órdenes, ni lotes, ni balances de masa.

- 3.1 Procesos: cada proceso en su página, paso a paso.
- 3.2 Métodos y parámetros: cómo se hace cada etapa y qué se controla en ella.
- 3.3 Productos y servicios: lo que el laboratorio entrega y con qué proceso.
"""
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.plantas_piloto.operacion.models.produccion import Producto, Receta
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

from apps.gestion_unidades.presentation.edicion_registro import ediciones_de
from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad
from apps.plantas_piloto.operacion.presentation.secciones_plantas import mapa_de


def procesos_de(unidad, borradores=False):
    """Los procesos activos con etapas, con todo lo que su página muestra.

    Con `borradores`, también los inactivos: quien gestiona la unidad los revisa en la ficha
    antes de activarlos, que es lo que los publica.
    """
    filtro = {} if borradores else {'activa': True}
    return list(
        Receta.objects.filter(unidad=unidad, etapas__isnull=False, **filtro).distinct()
        .select_related('producto', 'responsable')
        .prefetch_related('etapas__equipo', 'etapas__espacio', 'insumos__consumible', 'insumos__etapa',
                          'software', 'salidas__producto')
        .order_by('nombre')
    )


def productos_de(unidad, borradores=False):
    """Los productos y servicios públicos de la unidad, con los procesos que los entregan."""
    filtro = {} if borradores else {'publico': True}
    procesos = Receta.objects.all() if borradores else Receta.objects.filter(activa=True)
    return list(
        Producto.objects.filter(unidad=unidad, activo=True, **filtro)
        .prefetch_related(Prefetch('recetas', queryset=procesos.order_by('nombre')))
        .order_by('tipo', 'nombre')
    )


def con_metodo(procesos):
    """Los procesos que dicen cómo se hace alguna etapa o qué se controla en ella."""
    return [proceso for proceso in procesos
            if any(etapa.instrucciones or etapa.parametro for etapa in proceso.etapas.all())]


def duracion(minutos):
    """Minutos en palabras cortas: «45 min», «2 h», «1 h 30 min»."""
    horas, resto = divmod(int(minutos), 60)
    if not horas:
        return f'{resto} min'
    return f'{horas} h {resto} min' if resto else f'{horas} h'


def resumen_de(proceso):
    """Lo que el menú y las tarjetas dicen de un proceso: cuántas etapas y cuánto tarda."""
    etapas = list(proceso.etapas.all())
    total = sum(etapa.tiempo_total_min for etapa in etapas)
    partes = [f'{len(etapas)} etapa{"s" if len(etapas) != 1 else ""}']
    if total:
        partes.append(duracion(total))
    return ' · '.join(partes)


def _contexto(request, unidad, clave):
    mapa = mapa_de(unidad)
    numero = mapa.numero(clave) if mapa else ''
    modulo = mapa.modulo_de(numero) if numero else ''
    gestor = puede_gestionar_unidad(request.user, unidad)
    return {
        'unidad': unidad,
        'seccion': numero,
        'gestor': gestor,
        'volver_url': f'{unidad.get_absolute_url()}#{modulo}' if modulo else unidad.get_absolute_url(),
        'ediciones': ediciones_de(request.user, unidad),
    }


@xframe_options_sameorigin
def proceso_laboratorio_view(request, slug, proceso_id):
    """3.1: un proceso paso a paso, con lo que necesita y lo que entrega."""
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    procesos = procesos_de(unidad, borradores=puede_gestionar_unidad(request.user, unidad))
    proceso = next((proceso for proceso in procesos if proceso.pk == proceso_id), None)
    if proceso is None:
        raise Http404('El proceso no existe o no está activo')
    codigos = dict(UnidadEquipo.objects.filter(laboratorio=unidad, activa=True)
                   .values_list('equipo_id', 'codigo_unidad'))
    etapas = [{'etapa': etapa, 'ficha_equipo': codigos.get(etapa.equipo_id, ''),
               'insumos': [insumo for insumo in proceso.insumos.all() if insumo.etapa_id == etapa.pk]}
              for etapa in proceso.etapas.all()]
    return render(request, 'portal/pages/unidades/detalle/proceso_laboratorio.html', {
        **_contexto(request, unidad, 'procesos'),
        'proceso': proceso,
        'etapas': etapas,
        'insumos_generales': [insumo for insumo in proceso.insumos.all() if not insumo.etapa_id],
        'duracion_total': duracion(sum(etapa.tiempo_total_min for etapa in proceso.etapas.all())),
        'equipos': len({etapa.equipo_id for etapa in proceso.etapas.all() if etapa.equipo_id}),
        'otros': [otro for otro in procesos if otro.pk != proceso.pk],
        'revisar_borrador': not proceso.activa,
    })


@xframe_options_sameorigin
def metodos_laboratorio_view(request, slug):
    """3.2: cómo se hace cada etapa de cada proceso y qué se controla en ella."""
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    return render(request, 'portal/pages/unidades/detalle/metodos_laboratorio.html', {
        **_contexto(request, unidad, 'metodos'),
        'procesos': con_metodo(procesos_de(unidad, borradores=puede_gestionar_unidad(request.user, unidad))),
    })


@xframe_options_sameorigin
def productos_laboratorio_view(request, slug):
    """3.3: lo que el laboratorio entrega y con qué proceso lo hace."""
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    return render(request, 'portal/pages/unidades/detalle/productos_laboratorio.html', {
        **_contexto(request, unidad, 'productos'),
        'productos': productos_de(unidad, borradores=puede_gestionar_unidad(request.user, unidad)),
    })
