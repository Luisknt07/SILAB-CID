"""Catalogo publico de una tipologia institucional sin app propia.

Las cuatro tipologias implementadas conservan sus rutas historicas; aqui solo
se redirige a ellas. Una tipologia inactiva o desconocida responde 404 en el
servidor, no solo desaparece del menu.
"""

from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse

from apps.core.presentation.tipologias import idioma_actual
from apps.core.presentation.tipologias import tipologia as tipologia_por_codigo
from apps.directorio_unidades.contracts import TipoUnidad


def catalogo(request, tipologia):
    actual = tipologia_por_codigo(tipologia)
    if actual is None or not actual.activa:
        raise Http404
    if actual.codigo in {tipo.value for tipo in TipoUnidad}:
        return redirect(reverse(TipoUnidad(actual.codigo).ruta_catalogo))

    # La operacion heredada se carga al atender la peticion, no al importar.
    from apps.directorio_unidades.presentation.catalogo import catalogo_unidades

    return catalogo_unidades(
        request,
        actual.codigo,
        actual.codigo,
        actual.etiqueta(idioma_actual(), plural=True),
    )
