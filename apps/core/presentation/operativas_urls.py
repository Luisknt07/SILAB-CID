"""Rutas propietarias; controladores diferidos y precedencia conservada."""
from django.urls import path, re_path  # noqa: F401
from apps.core.routing.diferidas import vista_diferida

urlpatterns = [
    path("login/", vista_diferida('apps.core.usuarios.login_view'), name="login"),
    path("register/", vista_diferida('apps.core.usuarios.register_view'), name="register"),
    path("logout/", vista_diferida('apps.core.usuarios.salir'), name="logout"),
    path("profile/", vista_diferida('apps.core.usuarios.profile_view'), name="profile"),
    path("profile/edit/", vista_diferida('apps.core.usuarios.profile_edit_view'), name="profile_edit"),
]

for _ruta, _orden in zip(urlpatterns, (171, 172, 173, 174, 175), strict=True):
    _ruta.prioridad_proyecto = _orden
