from apps.gestion_unidades.admin.configuracion import BloqueoAgendaUnidadInline, CapacidadOperativaUnidadInline, ConfiguracionOperativaUnidadInline, EspacioReservableInline, HitoUnidadInline, HorarioOperacionUnidadInline, LineaAccionUnidadInline, MedioInteriorInline, NovedadUnidadInline, PresentacionUnidadInline, ResponsableUnidadInline
from apps.recursos.admin.contenido import ModuloUnidadInline, RecursoContenidoLocalInline, RecursoInline, ReglamentoUnidadInline, SoftwareInline, SolicitudMicroproyectoAdminMixin


from apps.core.presentation.administracion import AdministracionTraducida, TablaTraducida, BloqueTraducido

from apps.core.presentation.tipologias import (
    codigos_por_base, idioma_actual, nombre_tipologia, opciones_tipologias, tipologias_actuales,
)
from contextvars import ContextVar
import json

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.templatetags.static import static
from django.urls import NoReverseMatch, path, reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from apps.gestion_unidades.presentation.rutas_ficha import CAMPOS_DE_NAVEGACION, ancla_de_bloque, campos_planos, descripcion_de_ruta, grupo_de_bloque, grupo_de_campos, grupos_editor, orden_de_grupo, orden_de_partes, partes_de_bloque, partes_de_campos, rotulo
from apps.plantas_piloto.operacion.presentation.secciones_plantas import ajustes_de, mapa_de
from apps.directorio_unidades.presentation.ubicacion import miniatura, sedes_en_el_mapa, unidades_ubicadas

from apps.centros_experimentales.operacion.models.perfil import PerfilCentroExperimental
from apps.laboratorios.operacion.models.perfil import PerfilLaboratorio, PerfilPlataformaTecnologica
from apps.observatorios.operacion.models.perfil import PerfilObservatorio
from apps.plantas_piloto.operacion.models.perfil import PerfilPlantaPiloto
from apps.directorio_unidades.models.core import Unidad
from apps.directorio_unidades.models.relaciones import RelacionUnidad
from apps.directorio_unidades.models.sedes import SedeInstitucional






class PerfilOperativoInlineBase(BloqueTraducido):
    extra = 0
    max_num = 1
    can_delete = False
    classes = ['collapse']


class PerfilLaboratorioInline(PerfilOperativoInlineBase):
    model = PerfilLaboratorio
    fieldsets = (
        ('Operación del laboratorio', {
            'fields': (
                'activo', 'gestiona_practicas', 'gestiona_muestras',
                'requiere_protocolo', 'requiere_supervision',
                'acreditacion_referencia',
            ),
        }),
        ('Acceso', {
            'fields': ('descripcion_operativa', 'requisitos_acceso'),
        }),
    )


class PerfilPlantaPilotoInline(PerfilOperativoInlineBase):
    model = PerfilPlantaPiloto
    fieldsets = (
        ('Campañas, lotes y proceso', {
            'fields': (
                'activo', 'gestiona_campanias', 'gestiona_lotes',
                'duracion_minima_horas', 'requiere_receta_proceso',
                'requiere_control_calidad',
            ),
        }),
        ('Cierre operativo', {
            'fields': (
                'requiere_plan_limpieza', 'gestiona_residuos',
                'servicios_auxiliares',
            ),
        }),
        ('Acceso', {
            'fields': ('descripcion_operativa', 'requisitos_acceso'),
        }),
    )


class PerfilCentroExperimentalInline(PerfilOperativoInlineBase):
    model = PerfilCentroExperimental
    fieldsets = (
        ('Ensayos y ciclos experimentales', {
            'fields': (
                'activo', 'gestiona_areas_georreferenciadas', 'gestiona_ciclos',
                'requiere_material_biologico', 'requiere_protocolo_campo',
                'requiere_bioseguridad', 'variables_ambientales',
            ),
        }),
        ('Acceso', {
            'fields': ('descripcion_operativa', 'requisitos_acceso'),
        }),
    )


class PerfilObservatorioInline(PerfilOperativoInlineBase):
    model = PerfilObservatorio
    fieldsets = (
        ('Gobierno y acceso a datos', {
            'fields': (
                'activo', 'nivel_acceso_datos', 'gestiona_fuentes',
                'gestiona_versiones', 'publica_metodologia', 'ofrece_api',
                'ofrece_analisis_solicitud', 'periodicidad_actualizacion',
            ),
        }),
        ('Acceso', {
            'fields': ('descripcion_operativa', 'requisitos_acceso'),
        }),
    )


class PerfilPlataformaTecnologicaInline(PerfilOperativoInlineBase):
    model = PerfilPlataformaTecnologica
    fieldsets = (
        ('Operación tecnológica', {
            'fields': (
                'activo', 'permite_recursos_combinados',
                'acepta_archivos_tecnicos', 'gestiona_cotizaciones',
                'gestiona_ordenes_servicio', 'ofrece_asesoria',
            ),
        }),
        ('Acceso', {
            'fields': ('descripcion_operativa', 'requisitos_acceso'),
        }),
    )


PERFIL_INLINE_POR_CLASIFICACION = {
    'laboratorio_academico': PerfilLaboratorioInline,
    'laboratorio_id': PerfilLaboratorioInline,
    'laboratorio_mixto': PerfilLaboratorioInline,
    'planta_piloto': PerfilPlantaPilotoInline,
    'centro_experimental': PerfilCentroExperimentalInline,
    'observatorio': PerfilObservatorioInline,
    'plataforma_tecnologica': PerfilPlataformaTecnologicaInline,
}


















# ✅ AGREGAR: Inline para Software Disponible







# ✅ AGREGAR: Formulario personalizado para Recurso






# ✅ MEJORAR: Inline de Recurso con mejor manejo del contexto




class TipologiaUnidadFilter(admin.SimpleListFilter):
    """Filtra por tipologia con los nombres del catalogo, activas o no."""

    title = 'Tipo de unidad'
    parameter_name = 'dependencia'

    def lookups(self, request, model_admin):
        idioma = idioma_actual()
        return [(t.codigo, t.etiqueta(idioma)) for t in tipologias_actuales()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(dependencia=self.value())
        return queryset


class UnidadAdminForm(forms.ModelForm):
    """El limite de categorias se comprueba sobre la seleccion enviada.

    `Unidad.clean` solo puede leer las relaciones ya guardadas: al crear no hay
    clave primaria y al editar todavia contiene la seleccion anterior. Por eso
    la regla se aplica aqui, donde llegan las categorias del formulario.
    """

    # La tipologia sale del catalogo institucional: solo las activas se ofrecen
    # a una unidad nueva, y una unidad existente conserva la suya aunque este
    # desactivada.
    dependencia = forms.ChoiceField(label='Tipo de unidad', required=False)
    # Una seccion de vertical declara aqui las tipologias que admite; vacio
    # significa el catalogo entero, como en la lista general de unidades.
    codigos_permitidos = ()

    class Meta:
        model = Unidad
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        actual = self.instance.dependencia if self.instance.pk else None
        opciones = opciones_tipologias(incluir=actual)
        if self.codigos_permitidos:
            opciones = tuple(par for par in opciones if par[0] in self.codigos_permitidos)
        if 'dependencia' in self.fields:
            self.fields['dependencia'].choices = (('', '---------'), *opciones)
        # Las clasificaciones archivadas no se ofrecen, pero una unidad
        # existente conserva las que ya tiene asignadas.
        for campo in ('categorias', 'tipos_laboratorio'):
            if campo not in self.fields:
                continue
            consulta = self.fields[campo].queryset
            filtro = Q(activa=True)
            if self.instance.pk:
                filtro |= Q(pk__in=getattr(self.instance, campo).values_list('pk', flat=True))
            self.fields[campo].queryset = consulta.filter(filtro)

    def clean_dependencia(self):
        return self.cleaned_data.get('dependencia') or None

    def clean(self):
        datos = super().clean()
        dependencia = datos.get('dependencia')
        if dependencia:
            for campo in ('categorias', 'tipos_laboratorio'):
                fuera = [c.nombre for c in datos.get(campo) or () if not c.aplica_a(dependencia)]
                if fuera:
                    self.add_error(campo, (
                        'No se ofrecen para la tipología seleccionada: ' + ', '.join(fuera) + '.'
                    ))
        return datos

    def clean_categorias(self):
        categorias = self.cleaned_data['categorias']
        if len(categorias) > Unidad.MAXIMO_CATEGORIAS:
            raise ValidationError(
                'Una unidad puede tener máximo '
                f'{Unidad.MAXIMO_CATEGORIAS} categorías.'
            )
        return categorias


# ✅ MODIFICAR: ProyectoAdmin para incluir SoftwareInline
_PETICION_UNIDAD = ContextVar('peticion_unidad', default=None)


# El punto se marca en el mapa; latitud y longitud quedan a la vista para corregirlas a mano.
UBICACION_EN_EL_MAPA = ('Ubicación en el mapa', {
    'fields': ('ubicacion', 'piso', 'direccion', 'mapa_ubicacion', ('latitud', 'longitud')),
    'description': 'El punto y la dirección se muestran en la pestaña «Ubicación» de la ficha pública.',
})
IMAGEN_Y_VIDEO = ('Imagen y video', {
    'fields': ('imagen', ('credito_imagen', 'credito_imagen_url'), 'video_unidad'),
    'description': 'La imagen de portada de la unidad y su video de presentación.',
})
PLANO_Y_RECORRIDOS = ('Plano y recorridos', {
    'fields': ('plano_espacios', 'recorrido_espacios_youtube_url', 'recorrido_360_ruta'),
    'description': 'Lo que orienta antes de elegir un área: plano general, recorrido en video y tour 360°.',
})


def estatico_con_version(ruta, version):
    """Ruta absoluta con `?v=`: el navegador no reutiliza un mapa viejo guardado en caché."""
    return f'{static(ruta)}?v={version}'


VERSION_LEAFLET = '1.9.4'
VERSION_MAPA = '20260928-piso-foto-v1'
VERSION_EDITOR = '20260929-editor-grupos-v1'


class MapaEnEditorMixin:
    """Mapa para marcar el punto, con las sedes resaltadas y sus edificios."""
    ayuda_mapa = ''
    dibuja = False
    # Solo el editor de la unidad copia el punto de otra del mismo edificio.
    muestra_unidades = False

    class Media:
        css = {'all': (estatico_con_version('js/vendor/leaflet/leaflet.css', VERSION_LEAFLET),
                       estatico_con_version('portal/css/pages/unidades/mapa_unidad.css', VERSION_MAPA))}
        js = (estatico_con_version('js/vendor/leaflet/leaflet.js', VERSION_LEAFLET),
              estatico_con_version('portal/js/pages/unidades/mapa_unidad.js', VERSION_MAPA))

    @admin.display(description='Punto exacto')
    def mapa_ubicacion(self, obj):
        # La sede que se edita ya es el marcador: no se dibuja también como distintivo.
        excluir = obj.pk if isinstance(obj, SedeInstitucional) else None
        unidades = unidades_ubicadas(excluir=obj.pk if obj else None) if self.muestra_unidades else []
        imagen = miniatura(obj) if isinstance(obj, Unidad) else ''
        return format_html(
            '<div class="mapa-unidad-editor">'
            '<div class="mapa-unidad mapa-unidad--editor" data-mapa-editor{} data-sedes="{}" data-unidades="{}" '
            'data-imagen="{}" data-nombre="{}"></div><p class="mapa-unidad__ayuda">{}</p></div>',
            mark_safe(' data-dibujo' if self.dibuja else ''), json.dumps(sedes_en_el_mapa(excluir)),
            json.dumps(unidades), imagen, obj.nombre if obj else '', self.ayuda_mapa)










class RelacionUnidadInline(TablaTraducida):
    """Las relaciones que esta unidad ejerce (aloja, provee, analiza, sigue); la otra punta las ve solas."""
    model = RelacionUnidad
    fk_name = 'origen'
    extra = 0
    fields = ['tipo', 'destino', 'que_fluye', 'descripcion', 'activa', 'orden']
    autocomplete_fields = ['destino']
    verbose_name_plural = 'Relaciones con otras unidades (las que esta unidad ejerce)'
    classes = ['collapse']




def inlines_de_ficha(obj):
    """Los bloques de «Conoce la unidad» y de fotos por área: para toda unidad con ficha numerada."""
    if not obj or mapa_de(obj) is None:
        return []
    return [PresentacionUnidadInline, LineaAccionUnidadInline, HitoUnidadInline, MedioInteriorInline]


@admin.register(Unidad)
class UnidadAdmin(MapaEnEditorMixin, SolicitudMicroproyectoAdminMixin, AdministracionTraducida):
    ayuda_mapa = ('Haga clic en el mapa o arrastre el marcador; «Ir a una sede» lleva a cada sede. Al tocar un '
                  'edificio se proponen su nombre y la dirección si esos campos están vacíos. Las fotos son las '
                  'demás unidades ya ubicadas: al tocar una se copia su punto, para que las del mismo edificio '
                  'compartan marcador y se distingan por el piso.')
    muestra_unidades = True

    class Media(MapaEnEditorMixin.Media):
        # Muestra un grupo del editor a la vez y abre el bloque al que lleva un enlace del organizador.
        js = MapaEnEditorMixin.Media.js + (estatico_con_version('admin/js/editor_unidad.js', VERSION_EDITOR),)

    def changeform_view(self, request, *args, **kwargs):
        # Los campos de solo lectura no reciben la petición: el bloque de contenido
        # propio la necesita para mostrar solo lo que la persona puede abrir.
        marca = _PETICION_UNIDAD.set(request)
        try:
            respuesta = super().changeform_view(request, *args, **kwargs)
            # La plantilla se dibuja al final; se dibuja aquí, con la petición todavía a mano.
            return respuesta.render() if hasattr(respuesta, 'render') else respuesta
        finally:
            _PETICION_UNIDAD.reset(marca)

    def get_urls(self):
        from apps.gestion_unidades.admin.contenidos_ficha import nombre_de_la_vista
        opciones = self.model._meta
        return [path('<int:object_id>/contenidos/', self.admin_site.admin_view(self.contenidos_view),
                     name=nombre_de_la_vista(self)),
                path('<int:object_id>/estado/', self.admin_site.admin_view(self.estado_view),
                     name=f'{opciones.app_label}_{opciones.model_name}_estado'),
                *super().get_urls()]

    def estado_view(self, request, object_id):
        """Desactivar o reactivar la unidad y, si no tiene historial, eliminarla."""
        from apps.gestion_unidades.admin.estado_unidad import vista_estado
        return vista_estado(self, request, object_id)

    def contenidos_view(self, request, object_id):
        """Pestañas, secciones y carpetas propias de la ficha pública, para organizarlas."""
        from apps.gestion_unidades.admin.contenidos_ficha import vista_contenidos
        return vista_contenidos(self, request, object_id)

    @admin.display(description='Mapa del editor')
    def contenidos_de_la_ficha(self, obj):
        from django.template.loader import render_to_string
        from apps.gestion_unidades.admin.contenidos_ficha import url_contenidos
        if not obj or not obj.pk:
            return '—'
        mapa = mapa_de(obj)
        from apps.gestion_unidades.admin.estado_unidad import url_estado
        from apps.gestion_unidades.admin.tablero_unidad import url_tablero
        return render_to_string('admin/unidades/mapa_editor.html', {
            'activa': obj.activo,
            'estado_url': url_estado(self, obj),
            'grupos': grupos_editor(mapa),
            'contenidos_url': url_contenidos(self, obj),
            # El tablero existe en la sección de cada tipo, no en la lista general de unidades.
            'tablero_url': url_tablero(self, obj) if hasattr(self, 'tablero_view') else '',
            'es_planta': mapa is not None,
        })

    def _ordenar_bloques(self, secciones, obj):
        """Cada bloque va a su grupo del editor; con ficha numerada dice además a qué parte llega."""
        if not obj or not obj.pk:
            return secciones
        mapa = mapa_de(obj)
        ajustes = ajustes_de(obj) if mapa else {}
        ordenadas = []
        for nombre, opciones in secciones:
            campos = set(campos_planos(opciones.get('fields', ())))
            if 'contenidos_de_la_ficha' in campos:
                ordenadas.append((nombre, opciones))
                continue
            opciones = {**opciones, 'classes': (*opciones.get('classes', ()), f'grupo-editor-{grupo_de_campos(campos)}')}
            if mapa and nombre and not campos <= CAMPOS_DE_NAVEGACION:
                partes = partes_de_campos(campos, mapa)
                ruta = format_html('<span id="{}" class="ruta-ficha">{}</span>', ancla_de_bloque(nombre),
                                   descripcion_de_ruta(partes, ajustes, mapa))
                descripcion = opciones.get('description')
                nombre = rotulo(nombre, partes, ajustes, mapa)
                opciones['description'] = format_html('{} {}', ruta, descripcion) if descripcion else ruta
            ordenadas.append((nombre, opciones))
        return ordenadas

    def get_inline_instances(self, request, obj=None):
        instancias = super().get_inline_instances(request, obj)
        if not obj or not obj.pk:
            return instancias
        mapa = mapa_de(obj)
        ajustes = ajustes_de(obj) if mapa else {}
        for instancia in instancias:
            instancia.classes = [*(instancia.classes or ()), f'grupo-editor-{grupo_de_bloque(instancia.model.__name__)}']
            if mapa:
                # Con ficha numerada cada bloque dice también a qué sección llega.
                partes = partes_de_bloque(instancia.model.__name__, mapa)
                instancia.verbose_name_plural = rotulo(instancia.verbose_name_plural, partes, ajustes, mapa)
        return sorted(instancias, key=lambda instancia: (
            orden_de_grupo(grupo_de_bloque(instancia.model.__name__)),
            orden_de_partes(partes_de_bloque(instancia.model.__name__, mapa), mapa) if mapa else (3, 0)))

    @admin.display(description='Se edita en su propia pantalla')
    def contenido_propio(self, obj):
        from django.template.loader import render_to_string
        from apps.gestion_unidades.admin.tablero_unidad import tablero, url_tablero
        request = _PETICION_UNIDAD.get()
        mapa = mapa_de(obj)
        if not obj or not obj.pk or request is None or mapa is None:
            return '—'
        filas = [fila for grupo in tablero(request, obj, mapa.app_label)['ficha'] for fila in grupo['filas']]
        if not filas:
            return 'Su cuenta no tiene acceso a estas pantallas.'
        tabla = render_to_string('admin/unidades/tablero_filas.html', {'filas': filas, 'con_seccion': True})
        if not hasattr(self, 'tablero_view'):
            return tabla
        return format_html(
            '{}<p><a href="{}">Abrir el tablero de la unidad</a>: también reservas, prácticas, '
            'mantenimiento, inventario y expediente, organizados por su ficha.</p>', tabla, url_tablero(self, obj))

    def _alcance_local(self, request):
        from apps.gestion_unidades.admin.acceso import unidades_editables
        return not request.user.is_superuser and (
            unidades_editables(request.user).exists()
            or not request.user.has_perm('directorio_unidades.change_unidad'))

    def get_queryset(self, request):
        consulta = super().get_queryset(request)
        if self._alcance_local(request):
            from apps.gestion_unidades.admin.acceso import unidades_editables
            consulta = consulta.filter(pk__in=unidades_editables(request.user))
        return consulta

    def has_module_permission(self, request):
        return self.has_view_permission(request)

    def has_view_permission(self, request, obj=None):
        if self._alcance_local(request):
            consulta = self.get_queryset(request)
            return consulta.filter(pk=obj.pk).exists() if obj else consulta.exists()
        return super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if self._alcance_local(request):
            return self.has_view_permission(request, obj)
        return super().has_change_permission(request, obj)

    def has_add_permission(self, request):
        return not self._alcance_local(request) and super().has_add_permission(request)

    def get_actions(self, request):
        return {} if self._alcance_local(request) else super().get_actions(request)

    def get_list_filter(self, request):
        return [] if self._alcance_local(request) else super().get_list_filter(request)

    def get_fieldsets(self, request, obj=None):
        return self._ordenar_bloques(self.bloques_de_campos(request, obj), obj)

    def bloques_de_campos(self, request, obj=None):
        """Los bloques de campos del editor según el alcance de la cuenta, sin su ruta en la ficha."""
        if self._alcance_local(request):
            secciones = [
                ('Identidad institucional', {'fields': ('nombre', 'nombre_corto', 'codigo', 'dependencia', 'administrador'),
                 'description': 'La identidad y la administración principal las autoriza el superadministrador.'}),
                ('Datos y contenido de la unidad', {'fields': (
                    'descripcion', 'descripcion_corta', 'clasificacion_funcional',
                    'area_conocimiento', 'modo_operacion', 'categorias', 'tipos_laboratorio',
                    'fecha_inicio', 'fecha_fin', 'resolucion_numero', 'fecha_resolucion', 'horario_atencion',
                    'capacidad_personas', 'contacto_email', 'telefono', 'celular', 'sitio_web',
                )}),
                UBICACION_EN_EL_MAPA,
                IMAGEN_Y_VIDEO,
                PLANO_Y_RECORRIDOS,
            ]
        else:
            secciones = list(super().get_fieldsets(request, obj))
        if obj and obj.pk:
            # El mapa va primero: reparte el editor en grupos y lleva al organizador de la ficha.
            secciones.insert(0, ('Mapa del editor', {'fields': ('contenidos_de_la_ficha',)}))
        if obj and obj.pk and mapa_de(obj) is not None:
            tipo = {'plantas_piloto': 'de la planta', 'observatorios': 'del observatorio'}.get(obj.codigo_base,
                                                                                               'del laboratorio')
            secciones.append((f'Contenido propio {tipo}', {
                'fields': ('contenido_propio',),
                'description': 'La ficha pública arma solas sus secciones con estos datos; las carpetas propias '
                               'solo añaden material debajo de cada sección. Cree, edite o elimine desde aquí.',
            }))
        return secciones

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj)) + ['contenido_propio', 'contenidos_de_la_ficha']
        if not request.user.is_superuser:
            campos += ['nombre', 'nombre_corto', 'codigo', 'dependencia', 'administrador']
        return campos

    form = UnidadAdminForm
    list_display = [
        'nombre', 'nombre_corto', 'tipo_de_unidad', 'clasificacion_funcional',
        'area_conocimiento', 'activo', 'fecha_inicio',
    ]
    list_filter = [
        TipologiaUnidadFilter, 'clasificacion_funcional', 'area_conocimiento', 'activo',
    ]
    search_fields = ['nombre', 'nombre_corto']

    @admin.display(description='Tipo de unidad', ordering='dependencia')
    def tipo_de_unidad(self, unidad):
        # El codigo (`laboratorios`) es para el sistema; la persona lee el nombre.
        return nombre_tipologia(unidad.dependencia)
    inlines = [
        ConfiguracionOperativaUnidadInline, HorarioOperacionUnidadInline,
        CapacidadOperativaUnidadInline, BloqueoAgendaUnidadInline,
        ModuloUnidadInline, ReglamentoUnidadInline,
        SoftwareInline, EspacioReservableInline, ResponsableUnidadInline,
        RecursoInline, NovedadUnidadInline, RelacionUnidadInline,
    ]
    verbose_name = 'Laboratorio'
    verbose_name_plural = 'Laboratorios'
    filter_horizontal = ['categorias', 'tipos_laboratorio']

    fieldsets = (
        ('Información General', {
            'fields': ('nombre', 'nombre_corto', 'descripcion', 'descripcion_corta', 'slug', 'codigo')
        }),
        ('Clasificación', {
            'fields': (
                'dependencia', 'clasificacion_funcional', 'area_conocimiento',
                'modo_operacion', 'estado_catalogo', 'categorias',
                'tipos_laboratorio', 'activo',
            )
        }),
        ('Fechas y Gestión', {
            'fields': ('fecha_inicio', 'fecha_fin', 'administrador', 'resolucion_numero', 'fecha_resolucion')
        }),
        ('Atención', {
            'fields': ('facultad', 'adscrita_a', 'carreras', 'horario_atencion', 'capacidad_personas', 'contacto_email',
                       'telefono', 'celular', 'sitio_web', 'centro_vinculado'),
            'description': 'Datos operativos visibles en el visualizador público de la unidad.'
        }),
        UBICACION_EN_EL_MAPA,
        IMAGEN_Y_VIDEO,
        PLANO_Y_RECORRIDOS,
        ('Estadísticas', {
            'fields': ('visitas', 'likes', 'ultima_actualizacion'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['ultima_actualizacion', 'mapa_ubicacion']

    def has_delete_permission(self, request, obj=None):
        """La identidad maestra no se borra desde la lista: se retira en «Estado de la unidad».

        Allí se desactiva, conservando todo, o se elimina solo si no tiene historial.
        """
        return False

    def get_inlines(self, request, obj=None):
        if self._alcance_local(request):
            from apps.gestion_unidades.admin.autonomia import contenido_inline
            clases = [ModuloUnidadInline, ReglamentoUnidadInline, SoftwareInline,
                      EspacioReservableInline, RecursoContenidoLocalInline, NovedadUnidadInline]
            if obj:
                perfil = PERFIL_INLINE_POR_CLASIFICACION.get(obj.clasificacion_funcional)
                if perfil:
                    clases.insert(0, perfil)
            return [contenido_inline(clase) for clase in clases + inlines_de_ficha(obj)]
        inlines = list(super().get_inlines(request, obj))
        if not obj:
            return inlines

        perfil_inline = PERFIL_INLINE_POR_CLASIFICACION.get(
            obj.clasificacion_funcional,
        )
        if perfil_inline:
            inlines.insert(0, perfil_inline)
        return inlines + inlines_de_ficha(obj)


class SedeInstitucionalForm(forms.ModelForm):
    """Contorno y edificios viajan como JSON que escribe el mapa del editor."""

    class Meta:
        model = SedeInstitucional
        fields = '__all__'
        widgets = {'contorno': forms.HiddenInput, 'edificios': forms.HiddenInput}

    def clean_contorno(self):
        return self.cleaned_data['contorno'] or []

    def clean_edificios(self):
        return self.cleaned_data['edificios'] or []


@admin.register(SedeInstitucional)
class SedeInstitucionalAdmin(MapaEnEditorMixin, AdministracionTraducida):
    ayuda_mapa = ('Haga clic en el mapa o arrastre el marcador hasta la entrada de la sede. «Dibujar edificio» y '
                  '«Dibujar contorno» marcan los vértices uno a uno; al tocar una figura se renombra, se ajusta '
                  'arrastrando sus vértices o se elimina.')
    dibuja = True
    form = SedeInstitucionalForm
    list_display = ['nombre', 'localidad', 'en_el_mapa', 'total_edificios', 'orden', 'activa']
    list_filter = ['activa']
    search_fields = ['nombre', 'localidad', 'direccion']
    readonly_fields = ['mapa_ubicacion']
    fields = ['nombre', 'localidad', 'direccion', 'mapa_ubicacion', ('latitud', 'longitud'),
              ('contorno', 'edificios'), 'orden', 'activa']

    class Media(MapaEnEditorMixin.Media):
        js = MapaEnEditorMixin.Media.js + (estatico_con_version('portal/js/pages/unidades/dibujo_sede.js', VERSION_MAPA),)

    @admin.display(description='En el mapa', boolean=True)
    def en_el_mapa(self, sede):
        return sede.tiene_coordenadas

    @admin.display(description='Edificios')
    def total_edificios(self, sede):
        return len(sede.edificios)


























class UnidadDeTipologiaAdmin(UnidadAdmin):
    """Seccion propia de una vertical: solo sus unidades, nada de las demas.

    `base_tipologia` es la implementacion que reutiliza la vertical. La seccion
    reune todas las tipologias institucionales declaradas sobre esa base, de
    modo que anadir una modalidad nueva no exige tocar este codigo.
    """

    base_tipologia = ''

    def codigos(self):
        return codigos_por_base(self.base_tipologia)

    def get_urls(self):
        opciones = self.model._meta
        return [path('<int:object_id>/tablero/', self.admin_site.admin_view(self.tablero_view),
                     name=f'{opciones.app_label}_{opciones.model_name}_tablero'), *super().get_urls()]

    def tablero_view(self, request, object_id):
        """Todo lo de una unidad, con cada lista ya filtrada a ella."""
        from apps.gestion_unidades.admin.tablero_unidad import vista_tablero
        return vista_tablero(self, request, object_id)

    # Expedientes que cada unidad enlaza desde su fila: seccion de la vertical,
    # parametro del filtro y relacion inversa para contar.
    RECURSOS = (
        ('unidadequipo', 'laboratorio', 'unidades_equipo_principal', 'equipos'),
        ('consumible', 'unidad', 'consumibles_inventario', 'insumos'),
        ('reserva', 'laboratorio', 'reservas', 'reservas'),
    )

    def get_queryset(self, request):
        consulta = super().get_queryset(request).filter(dependencia__in=self.codigos())
        # Cada conteo en su subconsulta: contarlos juntos cruza equipos × insumos × reservas de cada unidad
        # (millones de filas para 27 unidades) y el administrador tardaba segundos en abrir cualquier página.
        aplicacion = self.model._meta.app_label
        return consulta.annotate(**{
            f'total_{etiqueta}': Coalesce(Subquery(
                self.model._meta.apps.get_model(aplicacion, modelo).objects.filter(**{parametro: OuterRef('pk')})
                .order_by().values(parametro).annotate(n=Count('pk')).values('n')[:1],
                output_field=IntegerField()), 0)
            for modelo, parametro, _, etiqueta in self.RECURSOS
        })

    @admin.display(description='Sus recursos')
    def recursos(self, unidad):
        """Una unidad con cientos de equipos e insumos abre los suyos, no los de todas."""
        enlaces = []
        for modelo, parametro, _, etiqueta in self.RECURSOS:
            try:
                url = reverse(f'admin:{self.model._meta.app_label}_{modelo}_changelist')
            except NoReverseMatch:
                continue
            enlaces.append((url, parametro, unidad.pk, getattr(unidad, f'total_{etiqueta}'), etiqueta))
        return format_html_join(' · ', '<a href="{}?{}__id__exact={}">{} {}</a>', enlaces)

    def get_list_display(self, request):
        columnas = list(super().get_list_display(request))
        if len(self.codigos()) == 1:
            columnas.remove('tipo_de_unidad')
        return columnas if self._alcance_local(request) else columnas + ['recursos']

    def get_changeform_initial_data(self, request):
        inicial = dict(super().get_changeform_initial_data(request))
        codigos = self.codigos()
        if len(codigos) == 1:
            inicial.setdefault('dependencia', codigos[0])
        return inicial

    def get_form(self, request, obj=None, **kwargs):
        formulario = super().get_form(request, obj, **kwargs)
        # Fuera de su seccion no se puede mover una unidad a otro tipo. La
        # restriccion viaja en una subclase: el campo declarado lo comparten
        # las cuatro secciones y tocarlo las cambiaria todas.
        return type('FormularioDeSeccion', (formulario,), {'codigos_permitidos': self.codigos()})

    def get_list_filter(self, request):
        # El filtro por tipo sobra cuando la seccion ya es de un solo tipo.
        return [f for f in super().get_list_filter(request) if f is not TipologiaUnidadFilter]
