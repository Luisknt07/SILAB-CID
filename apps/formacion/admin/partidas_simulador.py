"""Consulta de evidencia; el administrador no puede alterar estados ni puntajes."""

from django.contrib import admin
from apps.formacion.models.partidas_simulador import EventoPartida, PartidaSimulador, ParticipantePartida


class EvidenciaSoloLectura(admin.ModelAdmin):
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]


@admin.register(PartidaSimulador)
class PartidaSimuladorAdmin(EvidenciaSoloLectura):
    list_display = [
        "nombre",
        "unidad",
        "simulador",
        "caso",
        "fase",
        "version_motor",
        "revision",
        "actualizada_en",
    ]
    list_filter = ["simulador", "fase", "unidad"]
    list_select_related = ["unidad"]
    search_fields = ["nombre", "=codigo", "=id"]
    show_full_result_count = False
    list_per_page = 25


@admin.register(ParticipantePartida)
class ParticipantePartidaAdmin(EvidenciaSoloLectura):
    list_display = ["partida", "usuario", "rol", "unido_en"]
    list_filter = ["partida__unidad"]
    list_select_related = ["partida", "usuario"]
    show_full_result_count = False
    list_per_page = 25


@admin.register(EventoPartida)
class EventoPartidaAdmin(EvidenciaSoloLectura):
    list_display = ["partida", "revision", "tipo", "creado_en"]
    list_filter = ["partida__unidad"]
    list_select_related = ["partida"]
    show_full_result_count = False
    list_per_page = 25
