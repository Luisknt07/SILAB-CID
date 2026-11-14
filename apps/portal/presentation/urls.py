from django.urls import path

from apps.portal.presentation import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("favicon.ico", views.favicon, name="favicon"),
    path("quienes-somos/", views.QuienesSomosView.as_view(), name="quienes_somos"),
    path("servicios/", views.ServiciosView.as_view(), name="servicios_portal"),
    path("normativa/", views.NormativaView.as_view(), name="normativa"),
    path("noticias/", views.NoticiasView.as_view(), name="noticias"),
]
