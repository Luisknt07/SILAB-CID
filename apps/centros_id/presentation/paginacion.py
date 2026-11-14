"""Páginas pequeñas del dominio, con enlaces que conservan los filtros."""
from django.core.paginator import Paginator


def paginar(consulta, request, *, parametro='pagina', tamanio=25, fragmento=''):
    pagina = Paginator(consulta, tamanio).get_page(request.GET.get(parametro))

    def enlace(numero):
        parametros = request.GET.copy()
        parametros[parametro] = numero
        return '?' + parametros.urlencode() + fragmento

    return {'pagina': pagina,
            'anterior_url': enlace(pagina.previous_page_number()) if pagina.has_previous() else '',
            'siguiente_url': enlace(pagina.next_page_number()) if pagina.has_next() else ''}
