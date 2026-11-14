"""Permite tareas del panel en un marco del mismo origen, sin ampliar permisos."""
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

PREFIJOS_TRABAJO = ('/gestion/', '/admin/', '/reservas/', '/recursos-unidad/', '/laboratorio/')


def ruta_de_trabajo(path):
    return path.startswith(PREFIJOS_TRABAJO) and not path.endswith(
        ('/login/', '/logout/', '/password_change/', '/password_change/done/')
    )


class PanelTrabajoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        embedded = request.GET.get('_panel') == '1'
        if embedded:
            # Django admin interpreta parámetros desconocidos como filtros ORM.
            query = request.GET.copy()
            query.pop('_panel', None)
            request.GET = query
        response = self.get_response(request)
        user = getattr(request, 'user', None)
        if not (embedded and ruta_de_trabajo(request.path)
                and user and user.is_authenticated):
            return response
        if request.path.startswith('/admin/') and not user.is_staff:
            return response
        # Las vistas siguen comprobando unidad, rol, CSRF y estado del registro.
        if response.get('Content-Type', '').startswith('text/html'):
            response['X-Frame-Options'] = 'SAMEORIGIN'
        if response.status_code in (301, 302, 303, 307, 308) and response.get('Location'):
            destination = urlsplit(urljoin(request.build_absolute_uri(), response['Location']))
            origin = urlsplit(request.build_absolute_uri())
            if ((destination.scheme, destination.netloc) == (origin.scheme, origin.netloc)
                    and ruta_de_trabajo(destination.path)):
                query = [(key, value) for key, value in parse_qsl(destination.query, keep_blank_values=True)
                         if key != '_panel']
                query.append(('_panel', '1'))
                response['Location'] = urlunsplit(destination._replace(query=urlencode(query)))
        return response
