"""El escáner de equipos de la página de la unidad: cualquiera lee una etiqueta o un QR y llega al equipo.

Vive en «Equipos y fichas técnicas» del visor. Si el equipo es de la unidad, el visor abre su ficha; si es
de otra, se muestra lo público del equipo con la opción de ir a esa unidad; si no está (o no es público),
se dice que no existe. Solo datos públicos: el custodio, el valor y la historia quedan en la gestión.
"""
from urllib.parse import urlencode

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET

from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

from apps.recursos.presentation.codigos_equipo import PREFIJO_INSTITUCIONAL, buscar_equipo, codigo_leido, ve_datos_patrimoniales
from apps.recursos.presentation.equipo_publico import detalle_de_equipo
from apps.gestion_unidades.presentation.gobierno_editorial import objeto_visible_para


def equipo_publico_de(usuario, codigo):
    """El equipo que corresponde a la lectura, si el usuario puede verlo; si no, None (para él no existe)."""
    equipo = buscar_equipo(codigo, UnidadEquipo.objects.filter(laboratorio__isnull=False))
    if equipo is None or ve_datos_patrimoniales(usuario, equipo):
        return equipo
    if not equipo.activa or not equipo.laboratorio.activo or not objeto_visible_para(equipo, equipo.laboratorio, usuario):
        return None
    return equipo


def ficha_publica_del_escaner(usuario, equipo, unidad):
    """Lo que el escáner muestra del equipo leído desde la página de una unidad."""
    destino = equipo.laboratorio
    tipo = equipo.equipo
    detalle = detalle_de_equipo(destino, equipo, gestor=ve_datos_patrimoniales(usuario, equipo))
    ficha_url = reverse('ficha_equipo_publica', args=[destino.slug, equipo.codigo_unidad])
    return {
        'encontrado': True,
        'misma_unidad': destino.pk == unidad.pk or equipo.laboratorios.filter(pk=unidad.pk).exists(),
        'nombre': tipo.nombre,
        'marca_modelo': ' '.join(filter(None, (tipo.marca, tipo.modelo))),
        'familia': tipo.familia.nombre if tipo.familia_id else '',
        'codigo_bien': equipo.codigo_bien or '',
        'codigo_sistema': equipo.codigo_unidad,
        'unidad': destino.nombre,
        'estado': equipo.get_estado_unidad_display(),
        'disponible': equipo.estado_unidad == 'disponible',
        'imagen': detalle['imagen'],
        'icono': detalle['icono'],
        'areas': [area['espacio'].nombre for area in detalle['areas']],
        'caracteristicas': [[clave, valor] for clave, valor in detalle['caracteristicas'][:8]],
        'uso': tipo.uso_publico or '',
        'unidades': len(detalle['unidades']),
        'disponibles': detalle['disponibles'],
        'software': ([programa.nombre for programa in detalle['software']] or detalle['software_de_ficha'])[:12],
        'insumos': ([item.consumible.nombre for item in detalle['insumos']] or [str(nombre) for nombre in detalle['insumos_de_ficha']])[:12],
        'ficha_url': ficha_url,
        # Ir a la otra unidad: su página, con la ficha del equipo abierta en el visor.
        'unidad_url': f"{reverse('laboratorio_detalle', args=[destino.slug])}?{urlencode({'abrir': ficha_url})}",
    }


@xframe_options_sameorigin  # Se abre dentro del visor de la página de la unidad.
@require_GET
def escaner_unidad_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    return render(request, 'portal/pages/unidades/aula/escaner.html', {
        'unidad': unidad,
        'prefijo': PREFIJO_INSTITUCIONAL,
        'zxing': static('js/vendor/zxing-library-0.21.3.min.js'),
    })


@require_GET
def escaner_buscar_api(request, slug):
    """?codigo=<lectura> → el equipo (de esta u otra unidad) o que no existe."""
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    codigo = codigo_leido(request.GET.get('codigo', ''))
    equipo = equipo_publico_de(request.user, codigo) if codigo else None
    if equipo is None:
        return JsonResponse({'encontrado': False, 'codigo': codigo})
    return JsonResponse(ficha_publica_del_escaner(request.user, equipo, unidad))
