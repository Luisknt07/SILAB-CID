"""Avisos transversales; consultas diferidas hasta que la cabecera los utiliza."""
def reservation_notifications(request):
    """La cabecera solicita sus avisos; un PDF, modal o fragmento no los carga."""
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'reservation_notifications': (), 'reservation_notifications_unread': 0}
    from functools import lru_cache

    from django.utils.functional import SimpleLazyObject

    @lru_cache(maxsize=1)
    def recientes():
        from apps.reservas.models.reservas import NotificacionReserva
        from apps.documentos.models.avisos_documentales import AvisoDocumental

        reservas = NotificacionReserva.objects.filter(usuario=request.user).select_related(
            'reserva', 'reserva__laboratorio'
        )
        documentos = AvisoDocumental.objects.filter(usuario=request.user)
        avisos = sorted([*reservas[:6], *documentos[:6]], key=lambda aviso: aviso.creada_en, reverse=True)
        return avisos[:6]

    @lru_cache(maxsize=1)
    def sin_leer():
        from apps.reservas.models.reservas import NotificacionReserva
        from apps.documentos.models.avisos_documentales import AvisoDocumental

        return (NotificacionReserva.objects.filter(usuario=request.user, leida=False).count()
                + AvisoDocumental.objects.filter(usuario=request.user, leida=False).count())

    return {
        'reservation_notifications': SimpleLazyObject(recientes),
        'reservation_notifications_unread': SimpleLazyObject(sin_leer),
    }


def seguimiento_funcional(request):
    from django.utils.functional import SimpleLazyObject
    def habilitado():
        from apps.core.gobernanza import asignaciones_vigentes
        usuario = getattr(request, 'user', None)
        return bool(usuario and usuario.is_authenticated and usuario.is_active and
            (usuario.is_superuser or asignaciones_vigentes(usuario).exists()))
    return {'seguimiento_habilitado': SimpleLazyObject(habilitado)}
