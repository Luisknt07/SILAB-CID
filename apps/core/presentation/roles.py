"""Adaptador de politica operativa evaluada al consultar, sin acceso a datos."""

from django.conf import settings

from apps.core.roles import politica_roles


def roles_actuales():
    return politica_roles(settings.OPERATIONAL_ROLES)
