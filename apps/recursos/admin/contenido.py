
from apps.core.presentation.administracion import AdministracionTraducida, TablaTraducida, BloqueTraducido


from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join

from apps.recursos.presentation import despliegue_microproyectos, tipos_adjunto
from apps.gestion_unidades.presentation.rutas_ficha import ruta_de_carpeta, ruta_del_archivo
from apps.plantas_piloto.operacion.presentation.secciones_plantas import MAPAS, ajustes_de, mapa_de

from apps.recursos.models.recursos import ArchivoRecurso, CarpetaRecurso, DespliegueMicroproyecto, ModuloUnidad, Recurso, ReglamentoUnidad, SesionNavegador
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.software import SoftwareDisponible



from apps.directorio_unidades.presentation.contexto_editor import equipos_de_la_unidad, unidad_en_edicion


class ModuloUnidadInline(TablaTraducida):
    model = ModuloUnidad
    extra = 0
    fields = ['nombre', 'clave', 'icono', 'orden', 'activo', 'funcion_especial']
    readonly_fields = ['clave', 'funcion_especial']
    ordering = ['orden', 'id']
    classes = ['collapse']

    def funcion_especial(self, obj):
        if obj and obj.mostrar_herramientas_reserva:
            return 'Reservas y reglamento'
        return 'Contenido'
    funcion_especial.short_description = 'Función'


class ReglamentoUnidadInline(BloqueTraducido):
    model = ReglamentoUnidad
    extra = 0
    max_num = 1
    can_delete = False
    fields = [
        'activo', 'titulo', 'subtitulo', 'normas_generales',
        'reservas_horarios', 'equipos_materiales', 'seguridad',
        'contacto_texto', 'contacto_email',
    ]
    classes = ['collapse']


class CarpetaRecursoForm(forms.ModelForm):
    class Meta:
        model = CarpetaRecurso
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        unidad_id = self.instance.unidad_id if self.instance and self.instance.pk else None
        if 'seccion_planta' in self.fields:
            # Las secciones del mapa de su unidad; sin unidad todavía, las de todos los mapas.
            mapas = [mapa_de(self.instance.unidad)] if unidad_id else list(MAPAS.values())
            self.fields['seccion_planta'] = forms.ChoiceField(
                label='Sección de la ficha', required=False,
                choices=[('', '---------')] + [
                    (numero, f'{numero} · {datos["titulo"]}' + ('' if unidad_id else f' ({mapa.tipo})'))
                    for mapa in mapas if mapa is not None for numero, datos in mapa.secciones.items()
                ],
            )
        if unidad_id:
            if mapa_de(self.instance.unidad) is None:
                self.fields.pop('seccion_planta', None)
            self.fields['carpeta_padre'].queryset = CarpetaRecurso.objects.filter(del_expediente=False,
                unidad_id=unidad_id,
            ).exclude(pk=self.instance.pk)


class SoftwareInline(BloqueTraducido):
    # En fichas plegables: el selector de equipos no cabe en una fila de tabla.
    model = SoftwareDisponible
    extra = 0
    classes = ['collapse']
    fields = [
        'logo', 'codigo', 'nombre', 'version', 'tipo_recurso', 'tipo_acceso',
        'equipos_instalados', 'uso_en_equipo', 'licencias_totales',
        'licencias_disponibles', 'requiere_reserva', 'activo',
    ]
    filter_horizontal = ['equipos_instalados']

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'equipos_instalados':
            kwargs['queryset'] = equipos_de_la_unidad(request)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class RecursoInlineForm(forms.ModelForm):
    class Meta:
        model = Recurso
        fields = [
            'unidad', 'nombre', 'descripcion', 'carpeta', 'ficha',
            'archivo', 'url', 'navegador_remoto', 'tipo_adjunto', 'microproyecto_dependencias', 'autor',
            'fecha_documento',
            'fuente', 'licencia_uso', 'version', 'reemplaza_a', 'estado',
            'palabras_clave', 'orden', 'activo', 'visibilidad', 'descargar',
            'seguridad_verificada', 'autorizacion_tamano',
        ]
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['archivo'].help_text = (
            'Para HTML interactivo, el ZIP debe contener index.html. Para una aplicación Python, '
            'seleccione «Microproyecto Django»: cargue un ZIP con manage.py, requirements.txt '
            'y, opcionalmente, su SQLite inicial. Requiere puesta en marcha en un entorno independiente.'
        )
        tipo = self.fields['tipo_adjunto']
        tipo.required = False
        tipo.choices = tipos_adjunto.opciones_agrupadas()
        tipo.help_text = ('No es obligatorio. En «Automático» se asigna según el archivo: un ZIP con manage.py '
                          'se pone en marcha como microproyecto Django; HTML, ZIP interactivos, imágenes y videos '
                          'quedan como multimedia; hojas de datos, como dataset; y los enlaces, como publicación. '
                          'Elija otro tipo solo para clasificarlo mejor en el repositorio.')
        if not self.instance.pk:
            self.initial['tipo_adjunto'] = ''

        unidad_id = self.instance.unidad_id if self.instance else None
        if not unidad_id:
            unidad_inicial = self.initial.get('unidad')
            unidad_id = getattr(unidad_inicial, 'pk', unidad_inicial)
        if unidad_id:
            if 'ficha' in self.fields:
                self.fields['ficha'].queryset = self.fields['ficha'].queryset.filter(
                    unidad_id=unidad_id,
                ).order_by('codigo')
            reemplazos = self.fields['reemplaza_a'].queryset.filter(unidad_id=unidad_id).exclude(
                carpeta__del_expediente=True)
            if self.instance and self.instance.pk:
                reemplazos = reemplazos.exclude(pk=self.instance.pk)
            self.fields['reemplaza_a'].queryset = reemplazos.order_by('nombre')

        # Recurso existente: limitar las carpetas a su unidad.
        if self.instance and self.instance.unidad_id:
            unidad = self.instance.unidad
            base_queryset = CarpetaRecurso.objects.filter(del_expediente=False, unidad=unidad)
            # Incluir la carpeta actual si existe, para evitar errores de validación
            if self.instance.carpeta:
                base_queryset = base_queryset | CarpetaRecurso.objects.filter(pk=self.instance.carpeta.pk)
            self.fields['carpeta'].queryset = base_queryset

        # Nuevo recurso con unidad en initial (desde inline).
        elif 'initial' in kwargs and 'unidad' in kwargs['initial']:
            unidad = kwargs['initial']['unidad']
            self.fields['carpeta'].queryset = CarpetaRecurso.objects.filter(del_expediente=False,
                unidad=unidad
            )

        # En los inlines, formfield_for_foreignkey ya entrega el conjunto de
        # la unidad. No se reemplaza aquí para que una fila nueva sí pueda
        # elegir las carpetas que acaba de configurar el administrador.

    def clean(self):
        datos = super().clean()
        if not datos.get('tipo_adjunto'):
            archivo = datos.get('archivo')
            if archivo is None:  # Sin cambios: se conserva el archivo guardado.
                archivo = self.instance.archivo
            datos['tipo_adjunto'] = tipos_adjunto.inferir(archivo or None, datos.get('url') or '')
        return datos


class EnlaceRecursoAdminMixin:
    class Media:
        js = ('admin/js/enlace_recurso.js',)

    @admin.display(description='URL para abrir o compartir')
    def enlace_del_archivo(self, obj):
        if not obj or not obj.pk or not (obj.archivo or obj.url):
            return 'Guarde el archivo para generar su enlace automáticamente.'
        url = obj.get_url_compartir()
        return format_html(
            '<div class="enlace-recurso">'
            '<input type="text" readonly aria-label="URL del contenido" '
            'data-url-recurso="{}" value="{}"> '
            '<a href="{}" target="_blank" rel="noopener">Abrir como sitio</a> '
            '<button type="button" data-copiar-recurso>Copiar enlace</button> '
            '<span role="status" aria-live="polite"></span>'
            '<p class="help">Disponible según la visibilidad del recurso y su carpeta. '
            'El enlace reproduce el archivo guardado; guarde los cambios antes de abrirlo.</p></div>',
            url, url, url,
        )

    @admin.display(description='Entorno del microproyecto')
    def estado_microproyecto(self, obj):
        if not obj or not obj.pk or not obj.es_microproyecto:
            return 'Solo aplica al tipo «Microproyecto Django». Los demás archivos usan su visualizador habitual.'
        estado = despliegue_microproyectos.estado_visible(obj)
        boton = {'sin_solicitud': 'Poner en marcha', 'error': 'Reintentar', 'activo': 'Volver a desplegar'}
        return format_html(
            '<div class="estado-microproyecto" data-microproyecto-url="{}" data-estado="{}">'
            '<span role="status" aria-live="polite">{}</span>{}{}</div>',
            reverse('admin:recursos_recurso_microproyecto', args=[obj.pk]), estado['estado'], estado['texto'],
            format_html(' <a href="{}" target="_blank" rel="noopener">Abrir proyecto</a>', estado['url'])
            if estado['url'] else '',
            format_html(' <button type="button" data-desplegar-microproyecto>{}</button>', boton[estado['estado']])
            if estado['estado'] in boton else '',
        )


class SolicitudMicroproyectoAdminMixin:
    """Encola versiones nuevas solo si la instalación habilitó la automatización."""

    def _solicitar_microproyectos(self, request, recursos):
        for recurso in recursos:
            if isinstance(recurso, Recurso) and despliegue_microproyectos.solicitar_si_corresponde(recurso, request.user):
                messages.info(request, f'«{recurso.nombre}» quedó en cola para ponerse en marcha. '
                                       'El estado se actualiza en su ficha.')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        self._solicitar_microproyectos(request, [obj])

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        if formset.model is Recurso:
            self._solicitar_microproyectos(request, [f.instance for f in formset.forms
                                                     if f.instance.pk and f.has_changed()])


class RecursoInline(EnlaceRecursoAdminMixin, BloqueTraducido):
    model = Recurso
    form = RecursoInlineForm
    extra = 0
    fields = [
        'ubicacion_editor', 'nombre', 'descripcion', 'carpeta', 'ficha', 'archivo', 'enlace_del_archivo', 'url',
        'navegador_remoto', 'tipo_adjunto', 'estado_microproyecto', 'microproyecto_dependencias', 'autor', 'fecha_documento',
        'fuente', 'licencia_uso',
        'version', 'reemplaza_a', 'estado', 'palabras_clave', 'orden',
        'activo', 'visibilidad', 'descargar', 'seguridad_verificada',
        'autorizacion_tamano',
    ]
    verbose_name = 'Archivo o enlace'
    verbose_name_plural = 'Archivos y contenidos de la unidad'
    readonly_fields = ['ubicacion_editor', 'enlace_del_archivo', 'estado_microproyecto']
    classes = ['collapse']

    def get_queryset(self, request):
        # Los documentos del expediente los genera el sistema y se revisan en el Centro de reportes. Los demás
        # van juntos por carpeta, en el orden del menú, para que cada archivo quede al lado de sus hermanos.
        return super().get_queryset(request).exclude(carpeta__del_expediente=True).order_by(
            'carpeta__modulo_config__orden', 'carpeta__seccion_planta', 'carpeta__carpeta_padre__orden',
            'carpeta__orden', 'carpeta__nombre', 'orden', 'nombre', 'pk')

    @admin.display(description='Dónde se ve')
    def ubicacion_editor(self, obj):
        if not obj or not obj.pk:
            return format_html('<span id="recurso-editor-nuevo" class="ruta-ficha">{}</span>',
                               'La carpeta que elija decide en qué sección de la ficha se ve.')
        mapa = mapa_de(obj.unidad)
        ajustes = ajustes_de(obj.unidad) if mapa else {}
        ruta = ruta_del_archivo(obj, ajustes, mapa, {numero for numero, a in ajustes.items() if a.oculta})
        if ruta['lugares']:
            texto = format_html('Se ve en: {}', ' · '.join(ruta['lugares']))
        else:
            texto = ('No aparece en ninguna parte de la ficha: elíjale una carpeta, o complete descripción y tipo '
                     'y marque la verificación de seguridad para que entre al repositorio.')
        return format_html('<span id="recurso-editor-{}" class="ruta-ficha{}">{}</span>{}', obj.pk,
                           '' if ruta['lugares'] else ' ruta-ficha--sin-ruta', texto,
                           format_html_join('', '<small class="ruta-ficha__aviso">{}</small>',
                                            ((aviso,) for aviso in ruta['avisos'])))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Las carpetas de la unidad, cada una con su ruta en la ficha."""
        if db_field.name == 'carpeta':
            unidad = Unidad.objects.filter(pk=unidad_en_edicion(request)).first()
            kwargs['queryset'] = (
                CarpetaRecurso.objects.filter(del_expediente=False, unidad=unidad)
                .select_related('modulo_config', 'carpeta_padre', 'ficha')
                .order_by('modulo_config__orden', 'seccion_planta', 'carpeta_padre__orden', 'orden', 'nombre')
                if unidad else CarpetaRecurso.objects.none())
            campo = super().formfield_for_foreignkey(db_field, request, **kwargs)
            if unidad:
                mapa = mapa_de(unidad)
                ajustes = ajustes_de(unidad) if mapa else {}
                campo.label_from_instance = lambda carpeta: (
                    ruta_de_carpeta(carpeta, ajustes, mapa) or f'{carpeta.nombre} (sin ubicar: no se ve)')
            return campo
        if db_field.name == 'reemplaza_a' and 'queryset' not in kwargs:
            # También la fila vacía de plantilla, que se construye sin su unidad.
            kwargs['queryset'] = Recurso.objects.filter(unidad_id=unidad_en_edicion(request)).exclude(
                carpeta__del_expediente=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class RecursoContenidoLocalInline(RecursoInline):
    """Documentos de contenido, sin alterar informes emitidos ni controles de seguridad."""
    fields = [
        'ubicacion_editor', 'nombre', 'descripcion', 'carpeta', 'archivo', 'enlace_del_archivo', 'url', 'navegador_remoto', 'tipo_adjunto',
        'estado_microproyecto',
        'microproyecto_dependencias',
        'autor', 'fecha_documento', 'fuente', 'licencia_uso', 'version',
        'reemplaza_a', 'estado', 'palabras_clave', 'orden', 'activo',
        'visibilidad', 'descargar',
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(informe_mejora__isnull=True)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'reemplaza_a':
            kwargs['queryset'] = Recurso.objects.filter(
                unidad_id=unidad_en_edicion(request), informe_mejora__isnull=True).exclude(carpeta__del_expediente=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ConsultaAdmin(AdministracionTraducida):
    """Registros que produce el servicio: se consultan, no se editan."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DespliegueMicroproyecto)
class DespliegueMicroproyectoAdmin(ConsultaAdmin):
    list_display = ['recurso', 'estado', 'origen', 'solicitado_por', 'creado', 'terminado']
    list_filter = ['estado', 'origen', 'recurso__unidad']
    search_fields = ['recurso__nombre', 'detalle']


@admin.register(SesionNavegador)
class SesionNavegadorAdmin(ConsultaAdmin):
    list_display = ['recurso', 'usuario', 'estado', 'creada', 'ultima_actividad', 'expira']
    list_filter = ['estado', 'recurso__unidad']
    search_fields = ['recurso__nombre', 'usuario__username']
    exclude = ['token']
    actions = ['cerrar_sesiones']

    @admin.action(description='Cerrar las sesiones seleccionadas')
    def cerrar_sesiones(self, request, queryset):
        from django.utils import timezone
        queryset.filter(estado__in=('pendiente', 'iniciando', 'activa')).update(expira=timezone.now())


@admin.register(Recurso)
class RecursoAdmin(SolicitudMicroproyectoAdminMixin, EnlaceRecursoAdminMixin, AdministracionTraducida):
    form = RecursoInlineForm
    readonly_fields = ['enlace_del_archivo', 'estado_microproyecto']
    list_display = ['nombre', 'unidad', 'carpeta', 'orden', 'activo', 'visibilidad', 'descargar']
    list_filter = ['activo', 'visibilidad', 'descargar', 'unidad']
    search_fields = ['nombre', 'url', 'archivo']
    list_editable = ['orden', 'activo', 'visibilidad', 'descargar']
    ordering = ['unidad', 'carpeta__orden', 'orden', 'nombre']
    actions = ['publicar', 'restringir', 'hacer_internos', 'ocultar']

    def get_queryset(self, request):
        # Las versiones del expediente tienen su propia pantalla y transiciones.
        return super().get_queryset(request).filter(informe_mejora__isnull=True).exclude(
            carpeta__del_expediente=True)

    def get_urls(self):
        return [path('<int:object_id>/microproyecto/', self.admin_site.admin_view(self.microproyecto),
                     name='recursos_recurso_microproyecto'), *super().get_urls()]

    def microproyecto(self, request, object_id):
        """Estado en GET; en POST solo registra la solicitud, nunca ejecuta Docker."""
        from apps.gestion_unidades.admin.acceso import unidades_editables
        recurso = get_object_or_404(Recurso, pk=object_id, tipo_adjunto='microproyecto_django')
        if not (self.has_view_or_change_permission(request, recurso)
                or unidades_editables(request.user).filter(pk=recurso.unidad_id).exists()):
            return JsonResponse({'texto': 'No tiene acceso a este recurso.'}, status=403)
        if request.method == 'POST':
            if not despliegue_microproyectos.puede_solicitar(request.user):
                return JsonResponse({'texto': 'Su cuenta no tiene permiso para poner en marcha microproyectos.'},
                                    status=403)
            try:
                despliegue_microproyectos.solicitar(recurso, request.user, 'manual')
            except ValidationError as exc:
                return JsonResponse({'texto': ' '.join(exc.messages)}, status=400)
        elif request.method != 'GET':
            return JsonResponse({'texto': 'Método no permitido.'}, status=405)
        return JsonResponse(despliegue_microproyectos.estado_visible(recurso))

    @admin.action(description='Publicar los recursos seleccionados')
    def publicar(self, request, queryset):
        queryset.update(activo=True, visibilidad='publica')

    @admin.action(description='Restringir a la comunidad universitaria')
    def restringir(self, request, queryset):
        queryset.update(activo=True, visibilidad='restringida')

    @admin.action(description='Hacer internos para el personal de la unidad')
    def hacer_internos(self, request, queryset):
        queryset.update(activo=True, visibilidad='interna')

    @admin.action(description='Ocultar sin eliminar')
    def ocultar(self, request, queryset):
        queryset.update(activo=False)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filtrar carpetas según la unidad seleccionada."""
        if db_field.name == 'carpeta':
            # Si estamos editando un recurso existente
            if request.resolver_match and request.resolver_match.kwargs.get('object_id'):
                try:
                    recurso_id = request.resolver_match.kwargs['object_id']
                    recurso = Recurso.objects.get(pk=recurso_id)
                    if recurso.unidad:
                        kwargs['queryset'] = CarpetaRecurso.objects.filter(del_expediente=False, unidad=recurso.unidad)
                except Recurso.DoesNotExist:
                    pass

            # Aceptar el parámetro nuevo y el heredado durante la transición.
            elif 'unidad' in request.GET or 'proyecto' in request.GET:
                try:
                    unidad_id = int(request.GET.get('unidad') or request.GET['proyecto'])
                    kwargs['queryset'] = CarpetaRecurso.objects.filter(del_expediente=False, unidad_id=unidad_id)
                except (ValueError, TypeError):
                    pass

            # Si no hay contexto, no mostrar carpetas
            if 'queryset' not in kwargs:
                kwargs['queryset'] = CarpetaRecurso.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        """Personalizar el formulario para el admin standalone"""
        form = super().get_form(request, obj, **kwargs)

        if not obj and ('unidad' in request.GET or 'proyecto' in request.GET):
            try:
                unidad_id = int(request.GET.get('unidad') or request.GET['proyecto'])
                form.base_fields['carpeta'].queryset = CarpetaRecurso.objects.filter(del_expediente=False,
                    unidad_id=unidad_id
                )
            except (ValueError, TypeError):
                pass

        return form


@admin.register(CarpetaRecurso)
class CarpetaRecursoAdmin(AdministracionTraducida):
    form = CarpetaRecursoForm

    def get_exclude(self, request, obj=None):
        excluidos = list(super().get_exclude(request, obj) or ())
        if obj and mapa_de(obj.unidad) is None:
            excluidos.append('seccion_planta')
        return excluidos

    list_display = [
        'nombre', 'unidad', 'modulo_config', 'seccion_planta', 'carpeta_padre',
        'orden', 'activa', 'visibilidad',
    ]
    list_filter = ['activa', 'visibilidad', 'seccion_planta', 'modulo_config', 'unidad']
    search_fields = ['nombre', 'unidad__nombre']
    list_editable = ['orden', 'activa', 'visibilidad']
    ordering = ['unidad', 'modulo_config__orden', 'seccion_planta', 'orden', 'nombre']
    autocomplete_fields = ['unidad', 'modulo_config', 'carpeta_padre']


@admin.register(ModuloUnidad)
class ModuloUnidadAdmin(AdministracionTraducida):
    list_display = ['nombre', 'unidad', 'orden', 'activo', 'funcion_especial']
    list_filter = ['activo', 'unidad__dependencia']
    list_editable = ['orden', 'activo']
    search_fields = ['nombre', 'unidad__nombre']
    ordering = ['unidad', 'orden']
    prepopulated_fields = {'clave': ('nombre',)}
    fields = ['unidad', 'nombre', 'clave', 'icono', 'orden', 'activo', 'funcion_especial']
    readonly_fields = ['funcion_especial']

    def funcion_especial(self, obj):
        if obj and obj.mostrar_herramientas_reserva:
            return 'Reservas y reglamento'
        return 'Contenido'
    funcion_especial.short_description = 'Función'


@admin.register(ReglamentoUnidad)
class ReglamentoUnidadAdmin(AdministracionTraducida):
    list_display = ['unidad', 'titulo', 'contacto_email', 'activo']
    list_filter = ['activo', 'unidad__dependencia']
    search_fields = ['unidad__nombre', 'titulo']


@admin.register(ArchivoRecurso)
class ArchivoRecursoAdmin(AdministracionTraducida):
    list_display = ['tipo', 'archivo', 'url', 'fecha_subida']
    list_filter = ['tipo', 'fecha_subida']
