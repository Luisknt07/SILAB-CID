"""Los ejes productivos de los centros experimentales, con sus fotos, y su gestión productiva: los ciclos con su meta y
los registros del día. Los ejes se editan aquí o en su página; los registros, también en «Plan y registros de producción»."""
from apps.core.presentation.administracion import AdministracionTraducida, BloqueTraducido

from django.contrib import admin

from apps.centros_experimentales.operacion.models.centros import CicloProductivo, EjeProductivo, ImagenEje, RegistroProduccion
from apps.gestion_unidades.models.espacios import EspacioReservable


class ImagenEjeInline(BloqueTraducido):
    model = ImagenEje
    extra = 0
    fields = ('imagen', 'titulo', 'credito', 'fuente', 'orden')


@admin.register(EjeProductivo)
class EjeProductivoAdmin(AdministracionTraducida):
    list_display = ('titulo', 'unidad', 'orden', 'publicado')
    list_filter = ('unidad', 'publicado')
    search_fields = ('titulo', 'resumen', 'que_produce', 'rubros')
    autocomplete_fields = ('unidad',)
    list_editable = ('orden', 'publicado')
    filter_horizontal = ('espacios',)
    inlines = (ImagenEjeInline,)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # Las áreas que se ofrecen son las del centro del eje; al crearlo, las de todos los centros.
        if db_field.name == 'espacios':
            consulta = EspacioReservable.objects.filter(unidad__dependencia='centro_experimental')
            pk = request.resolver_match.kwargs.get('object_id') if request.resolver_match else None
            eje = EjeProductivo.objects.filter(pk=pk).first() if pk else None
            kwargs['queryset'] = (consulta.filter(unidad=eje.unidad) if eje else consulta).order_by('unidad', 'orden')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class RegistroProduccionInline(BloqueTraducido):
    model = RegistroProduccion
    extra = 0
    fields = ('fecha', 'tipo', 'cantidad', 'unidad_medida', 'destino', 'detalle', 'registrado_por')
    readonly_fields = ('registrado_por',)
    ordering = ('-fecha', '-pk')


@admin.register(CicloProductivo)
class CicloProductivoAdmin(AdministracionTraducida):
    list_display = ('nombre', 'eje', 'rubro', 'es_ensayo', 'inicio', 'fin_previsto', 'meta', 'unidad_medida', 'estado')
    list_filter = ('eje__unidad', 'es_ensayo', 'estado', 'tipo')
    search_fields = ('nombre', 'rubro', 'eje__titulo', 'objetivo')
    autocomplete_fields = ('eje', 'responsable')
    date_hierarchy = 'inicio'
    inlines = (RegistroProduccionInline,)

    def save_formset(self, request, form, formset, change):
        # Quien anota un registro desde aquí queda como quien lo registró.
        for registro in formset.save(commit=False):
            if isinstance(registro, RegistroProduccion) and registro.registrado_por_id is None:
                registro.registrado_por = request.user
            registro.save()
        for eliminado in formset.deleted_objects:
            eliminado.delete()
        formset.save_m2m()


@admin.register(RegistroProduccion)
class RegistroProduccionAdmin(AdministracionTraducida):
    list_display = ('fecha', 'ciclo', 'tipo', 'cantidad', 'unidad_medida', 'destino', 'registrado_por')
    list_filter = ('ciclo__eje__unidad', 'tipo', 'destino')
    search_fields = ('ciclo__nombre', 'detalle')
    autocomplete_fields = ('ciclo',)
    date_hierarchy = 'fecha'
    readonly_fields = ('registrado_por',)

    def save_model(self, request, obj, form, change):
        if obj.registrado_por_id is None:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)
