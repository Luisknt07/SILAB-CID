LABORATORIOS_ROUTES = {
    'laboratorios_unidades',
    'hublab',
    'observatorios',
    'centros-experimentales',
    'plantas-piloto',
    'laboratorio_detalle',
    'observatorio_detalle',
    'centro_experimental_detalle',
    'planta_piloto_detalle',
}


def institutional_navigation(request):
    """Identifica la pestaña institucional activa para la cabecera global."""
    resolver_match = getattr(request, 'resolver_match', None)
    route_name = resolver_match.url_name if resolver_match else ''
    controller_module = getattr(getattr(resolver_match, 'func', None), '__module__', '')
    route_map = {
        'home': 'inicio',
        'quienes_somos': 'quienes',
        'centros_id': 'centros',
        'servicios_portal': 'servicios',
        'normativa': 'normativa',
        'noticias': 'noticias',
    }
    if controller_module.startswith('apps.centros_id.'):
        active_page = 'centros'
    elif route_name in LABORATORIOS_ROUTES:
        active_page = 'laboratorios'
    else:
        active_page = route_map.get(route_name, '')
    return {'institutional_active_page': active_page}
