"""Administración de lo propio de los observatorios: indicadores con sus valores, publicaciones, encuestas, aliados
solicitudes de datos, tableros, visores externos, la política de datos y las descargas. Lo mismo se edita desde las páginas del observatorio; aquí se ve todo junto."""

from apps.core.presentation.administracion import AdministracionTraducida, BloqueTraducido

from django.contrib import admin

from apps.observatorios.operacion.models.observatorios import AliadoObservatorio, ConectorIndicador, DescargaDatos, EncuestaObservatorio, FuenteDatos, ImagenLinea, IndicadorObservatorio, LineaObservatorio, PoliticaDatosObservatorio, PublicacionObservatorio, RevisionValor, SolicitudDatos, TableroObservatorio, ValorIndicador, VisorExterno


class ValorIndicadorInline(BloqueTraducido):
    model = ValorIndicador
    extra = 0
    fields = ('periodo', 'fecha', 'territorio', 'valor', 'provisional', 'nota', 'origen')
    readonly_fields = ('origen',)
    ordering = ('territorio', '-fecha')


class ConectorIndicadorInline(BloqueTraducido):
    model = ConectorIndicador
    extra = 0
    fields = ('tipo', 'parametros', 'frecuencia_horas', 'activo', 'estado', 'ultima_ejecucion', 'mensaje')
    readonly_fields = ('estado', 'ultima_ejecucion', 'mensaje')


@admin.register(IndicadorObservatorio)
class IndicadorObservatorioAdmin(AdministracionTraducida):
    list_display = ('nombre', 'unidad', 'linea', 'unidad_medida', 'periodicidad', 'fuente_datos', 'publicado')
    list_filter = ('unidad', 'linea', 'periodicidad', 'tipo_fuente', 'publicado')
    search_fields = ('nombre', 'codigo', 'definicion', 'fuente')
    autocomplete_fields = ('unidad', 'fuente_datos')
    list_editable = ('publicado',)
    ordering = ('unidad', 'orden', 'nombre')
    inlines = (ConectorIndicadorInline, ValorIndicadorInline)


@admin.register(PublicacionObservatorio)
class PublicacionObservatorioAdmin(AdministracionTraducida):
    list_display = ('titulo', 'unidad', 'tipo', 'fecha_planificada', 'estado', 'fecha_publicada')
    list_filter = ('unidad', 'tipo', 'estado')
    search_fields = ('titulo', 'periodo', 'resumen')
    autocomplete_fields = ('unidad',)
    filter_horizontal = ('indicadores',)
    date_hierarchy = 'fecha_planificada'


@admin.register(EncuestaObservatorio)
class EncuestaObservatorioAdmin(AdministracionTraducida):
    list_display = ('nombre', 'unidad', 'periodicidad', 'ultimo_levantamiento', 'activa')
    list_filter = ('unidad', 'periodicidad', 'activa')
    search_fields = ('nombre', 'objetivo', 'poblacion')
    autocomplete_fields = ('unidad',)


@admin.register(AliadoObservatorio)
class AliadoObservatorioAdmin(AdministracionTraducida):
    list_display = ('nombre', 'unidad', 'tipo', 'rol', 'convenio', 'activo')
    list_filter = ('unidad', 'tipo', 'rol', 'activo')
    search_fields = ('nombre', 'aporte', 'convenio')
    autocomplete_fields = ('unidad',)


@admin.register(SolicitudDatos)
class SolicitudDatosAdmin(AdministracionTraducida):
    list_display = ('unidad', 'usuario', 'tipo', 'estado', 'creada', 'atendida')
    list_filter = ('unidad', 'tipo', 'estado')
    search_fields = ('descripcion', 'finalidad', 'institucion', 'usuario__username')
    autocomplete_fields = ('unidad', 'usuario')
    readonly_fields = ('usuario', 'creada')


@admin.register(TableroObservatorio)
class TableroObservatorioAdmin(AdministracionTraducida):
    list_display = ('titulo', 'unidad', 'linea', 'vista', 'orden', 'publicado')
    list_filter = ('unidad', 'linea', 'vista', 'publicado')
    search_fields = ('titulo', 'descripcion')
    autocomplete_fields = ('unidad',)
    filter_horizontal = ('indicadores',)


@admin.register(VisorExterno)
class VisorExternoAdmin(AdministracionTraducida):
    list_display = ('titulo', 'unidad', 'linea', 'plataforma', 'institucion', 'fecha_corte', 'publicado')
    list_filter = ('unidad', 'linea', 'plataforma', 'publicado')
    search_fields = ('titulo', 'descripcion', 'responsable')
    autocomplete_fields = ('unidad',)


@admin.register(PoliticaDatosObservatorio)
class PoliticaDatosObservatorioAdmin(AdministracionTraducida):
    list_display = ('unidad', 'licencia', 'actualizada')
    list_filter = ('unidad',)
    autocomplete_fields = ('unidad',)


@admin.register(DescargaDatos)
class DescargaDatosAdmin(AdministracionTraducida):
    list_display = ('fecha', 'unidad', 'formato', 'conjunto', 'veces')
    list_filter = ('unidad', 'formato')
    date_hierarchy = 'fecha'

    def has_add_permission(self, request):
        return False  # Las cuenta el portal al descargar; no se escriben a mano.

    def has_change_permission(self, request, obj=None):
        return False


class ImagenLineaInline(BloqueTraducido):
    model = ImagenLinea
    extra = 0
    fields = ('imagen', 'titulo', 'credito', 'fuente', 'orden')


@admin.register(LineaObservatorio)
class LineaObservatorioAdmin(AdministracionTraducida):
    list_display = ('titulo', 'unidad', 'orden', 'publicada')
    list_filter = ('unidad', 'publicada')
    search_fields = ('titulo', 'resumen', 'que_estudia')
    autocomplete_fields = ('unidad',)
    list_editable = ('orden', 'publicada')
    inlines = (ImagenLineaInline,)


@admin.register(FuenteDatos)
class FuenteDatosAdmin(AdministracionTraducida):
    list_display = ('nombre', 'institucion', 'metodo', 'acceso', 'periodicidad', 'requiere_clave')
    list_filter = ('metodo', 'acceso', 'requiere_clave')
    search_fields = ('nombre', 'institucion', 'descripcion')


@admin.register(ConectorIndicador)
class ConectorIndicadorAdmin(AdministracionTraducida):
    list_display = ('indicador', 'tipo', 'frecuencia_horas', 'activo', 'estado', 'ultima_ejecucion')
    list_filter = ('indicador__unidad', 'tipo', 'estado', 'activo')
    readonly_fields = ('ultima_ejecucion', 'estado', 'mensaje', 'nuevos', 'actualizados')


@admin.register(RevisionValor)
class RevisionValorAdmin(AdministracionTraducida):
    list_display = ('fecha', 'valor', 'anterior', 'nuevo', 'origen')
    list_filter = ('valor__indicador__unidad', 'origen')
    date_hierarchy = 'fecha'

    def has_add_permission(self, request):
        return False  # Las deja el propio valor al corregirse; el historial no se escribe a mano.

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
