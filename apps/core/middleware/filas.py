"""Identidad RLS local a la transacción, nunca persistente en conexiones reutilizadas."""
from django.conf import settings
from django.db import connection, transaction


class ContextoFilasMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, 'RLS_ENABLED', False):
            return self.get_response(request)
        from apps.gestion_unidades.presentation.permisos import unidades_gestionables, puede_operar_modulo_unidad

        user = request.user
        active = user.is_authenticated and user.is_active
        uid = str(user.pk) if active else '0'
        units = ','.join(str(unit.pk) for unit in unidades_gestionables(user)
                         if puede_operar_modulo_unidad(user, unit, 'practicas')) if active and not user.is_superuser else ''
        # La transacción también incluye el renderizado de TemplateResponse.
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('slcid.user_id', %s, true), "
                               "set_config('slcid.superuser', %s, true), "
                               "set_config('slcid.units', %s, true)",
                               [uid, 'on' if active and user.is_superuser else 'off', units])
            response = self.get_response(request)
            if hasattr(response, 'render') and not response.is_rendered:
                response.render()
            return response
