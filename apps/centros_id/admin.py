"""Administración propia de los Centros I+D, aparte de las unidades.

El centro se edita en una sola ficha con su gobierno, su ruta, sus líneas, sus espacios y planos, sus fases, su
presupuesto, sus indicadores, sus riesgos, su articulación, las relaciones entre sus áreas y los ajustes de sus
secciones. Lo que crece a diario tiene su propia lista: las áreas con sus equipos y procesos, el equipo humano, los
proyectos, los resultados, los casos de éxito, los aliados, las convocatorias, las novedades, los documentos, las
carpetas de contenido, el portafolio y las solicitudes.
"""

import json
from copy import copy

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.db.models import TextField
from django.templatetags.static import static
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect

from apps.core.presentation.administracion import AdministracionTraducida, BloqueTraducido, TablaTraducida

from .formularios import CentroIDForm
from .identidades import identidad_de, principal_vigente
from .models import (
    AjusteSeccion, Aliado, Articulacion, CarpetaCentro, CasoExito, CentroID, Componente, Convocatoria, DocumentoCentro,
    EquipoCentro, EtapaOperativa, Fase, Grupo, HitoProyecto, ImagenCentro, Indicador, Integrante, LineaInvestigacion, Modalidad,
    Novedad, OrganoGobierno, PartidaPresupuesto, PasoProceso, PlanoCentro, ProcesoArea, Proyecto, RecursoCentro,
    RelacionArea, Resultado, Riesgo, Servicio, SolicitudCentro, Zona,
    BloqueoRecurso, HabilitacionEquipo, HerramientaCentro, HorarioRecurso, RegistroSolicitud,
    SesionAcompanamiento, TareaSolicitud,
)

TEXTO_CORTO = {TextField: {'widget': forms.Textarea(attrs={'rows': 3})}}


def _ruta_centro(modelo):
    if modelo is CentroID:
        return 'pk'
    if any(c.name == 'centro' for c in modelo._meta.fields):
        return 'centro_id'
    return {EquipoCentro: 'componente__centro_id', ProcesoArea: 'componente__centro_id',
            PasoProceso: 'proceso__componente__centro_id', HitoProyecto: 'proyecto__centro_id',
            RecursoCentro: 'carpeta__centro_id', SesionAcompanamiento: 'solicitud__centro_id',
            TareaSolicitud: 'solicitud__centro_id'}.get(modelo, '')


def _acotar_campos(formulario, centro_id=None, propios=None):
    for nombre, campo in tuple(formulario.base_fields.items()):
        if not isinstance(campo, (forms.ModelChoiceField, forms.ModelMultipleChoiceField)):
            continue
        ruta = _ruta_centro(campo.queryset.model)
        if not ruta:
            continue  # Las cuentas se eligen en auth mediante CuentaChoiceField.
        acotado = copy(campo)
        if propios is not None:
            acotado.queryset = acotado.queryset.filter(**{ruta + '__in': propios})
        if centro_id is not None:
            acotado.queryset = acotado.queryset.filter(**{ruta: centro_id})
        formulario.base_fields[nombre] = acotado


class _Tabla(TablaTraducida):
    extra = 0
    classes = ['collapse']
    formfield_overrides = TEXTO_CORTO


class _DelCentro:
    """Las listas que se filtran por centro y, para quien no administra la plataforma, solo muestran sus centros."""
    campo_centro = 'centro'

    def get_queryset(self, request):
        consulta = super().get_queryset(request)
        if request.user.is_superuser:
            return consulta
        propios = CentroID.objects.filter(responsable_id=request.user.pk) | CentroID.objects.filter(gestores__pk=request.user.pk)
        return consulta.filter(**{f'{self.campo_centro}__in': propios.distinct()})

    def _centro_edicion(self, request, obj):
        partes = self.campo_centro.split('__')
        if request.method == 'POST' and partes[0] in request.POST:
            valor = request.POST.get(partes[0], '')
            if not valor.isascii() or not valor.isdigit() or len(valor) > 18:
                return 0  # La validación normal del formulario mostrará el error.
            relacionado = self.model._meta.get_field(partes[0]).remote_field.model
            centro = relacionado.objects.filter(pk=int(valor)).first()
            partes = partes[1:]
        else:
            centro = obj
        if centro is None:
            return None if obj is None and request.method != 'POST' else 0
        for parte in partes:
            centro = getattr(centro, parte)
        return centro.pk

    def _acotar_formulario(self, request, formulario, obj):
        principal = principal_vigente(request.user)
        propios = None if principal and principal.is_superuser else CentroID.objects.filter(
            models.Q(responsable_id=principal.pk) | models.Q(gestores__pk=principal.pk)
        ).distinct() if principal else CentroID.objects.none()
        _acotar_campos(formulario, self._centro_edicion(request, obj), propios)

    def get_form(self, request, obj=None, change=False, **kwargs):
        formulario = super().get_form(request, obj, change=change, **kwargs)
        self._acotar_formulario(request, formulario, obj)
        return formulario

    def get_formsets_with_inlines(self, request, obj=None):
        for formulario, inline in super().get_formsets_with_inlines(request, obj):
            self._acotar_formulario(request, formulario.form, obj)
            yield formulario, inline


    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            modelo = db_field.remote_field.model
            propios = CentroID.objects.filter(models.Q(responsable_id=request.user.pk) | models.Q(gestores__pk=request.user.pk)).distinct()
            if modelo is CentroID:
                kwargs['queryset'] = propios
            else:
                nombres = {f.name for f in modelo._meta.fields}
                ruta = ('centro' if 'centro' in nombres else 'componente__centro' if modelo is EquipoCentro
                        else 'solicitud__centro' if 'solicitud' in nombres else '')
                if ruta:
                    kwargs['queryset'] = modelo.objects.filter(**{ruta + '__in': propios})
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        centro = obj
        for parte in self.campo_centro.split('__'):
            centro = getattr(centro, parte)
        if not centro.puede_gestionar(request.user):
            raise PermissionDenied
        super().save_model(request, obj, form, change)


class _ContenidoDelCentro(_DelCentro):
    actions = ['validar_contenido']

    def get_readonly_fields(self, request, obj=None):
        return tuple(super().get_readonly_fields(request, obj)) + ('es_muestra', 'validado_en', 'validado_por')

    def get_list_display(self, request):
        return tuple(super().get_list_display(request)) + ('es_muestra', 'validado_en')

    def get_list_filter(self, request):
        return tuple(super().get_list_filter(request)) + ('es_muestra',)

    @admin.action(description=_('Validar procedencia y retirar la marca de muestra'), permissions=['change'])
    def validar_contenido(self, request, consulta):
        for objeto in consulta:
            try:
                objeto.validar(request.user)
            except ValidationError as error:
                self.message_user(request, f'{objeto}: {" ".join(error.messages)}', messages.WARNING)
                continue
            self.log_change(request, objeto, 'Procedencia validada; contenido institucional.')
            self.message_user(request, f'{objeto}: procedencia validada.', messages.SUCCESS)


class GobiernoInline(BloqueTraducido):
    model = OrganoGobierno
    extra = 0
    classes = ['collapse']
    formfield_overrides = {TextField: {'widget': forms.Textarea(attrs={'rows': 4})}}
    fields = (('nombre', 'rol', 'icono', 'orden'), 'responsabilidad', 'funciones')


class RutaInline(_Tabla):
    model = EtapaOperativa
    fields = ('numero', 'nombre', 'proposito', 'responsable', 'resultado')


class ModalidadInline(_Tabla):
    model = Modalidad
    fields = ('nombre', 'proposito', 'usuarios', 'icono', 'orden')


class LineaInline(_Tabla):
    model = LineaInvestigacion
    fields = ('nombre', 'resultados', 'retos', 'retos_muestra', 'componente', 'orden')


class ZonaInline(_Tabla):
    model = Zona
    fields = ('codigo', 'nombre', 'nivel', 'dimensiones', 'area_m2', 'componente', 'reservable', 'plano_x', 'plano_y',
              'orden')


class PlanoInline(_Tabla):
    model = PlanoCentro
    fields = ('nivel', 'titulo', 'imagen', 'credito', 'orden')


class RelacionAreaInline(_Tabla):
    model = RelacionArea
    fields = ('origen', 'destino', 'que_fluye', 'orden')


class FaseInline(_Tabla):
    model = Fase
    fields = ('numero', 'nombre', 'actividades', 'horizonte', 'estado')


class PresupuestoInline(_Tabla):
    model = PartidaPresupuesto
    fields = ('concepto', 'contenido', 'monto', 'nota', 'orden')


class IndicadorInline(_Tabla):
    model = Indicador
    fields = ('categoria', 'nombre', 'medicion', 'calculo', 'meta', 'valor', 'actualizado', 'orden')


class RiesgoInline(_Tabla):
    model = Riesgo
    fields = ('categoria', 'riesgo', 'efecto', 'mitigacion', 'orden')


class ArticulacionInline(_Tabla):
    model = Articulacion
    fields = ('tipo', 'actor', 'forma', 'unidad_slug', 'modalidad', 'instrumento', 'vigencia_hasta', 'reglas', 'orden')


class ImagenCentroInline(_Tabla):
    model = ImagenCentro
    fields = ('imagen', 'titulo', 'credito', 'fuente', 'componente', 'es_plano', 'orden')


class AjusteInline(_Tabla):
    model = AjusteSeccion
    fields = ('clave', 'titulo', 'oculta')


@admin.register(CentroID)
class CentroIDAdmin(AdministracionTraducida):
    form = CentroIDForm
    list_display = ('orden', 'nombre', 'sigla', 'nombre_area', 'estado', 'responsable', 'activo')
    list_display_links = ('nombre',)
    list_filter = ('area', 'estado', 'activo')
    search_fields = ('nombre', 'sigla', 'proposito')
    ordering = ('orden', 'nombre')
    prepopulated_fields = {'slug': ('nombre',)}
    formfield_overrides = {TextField: {'widget': forms.Textarea(attrs={'rows': 4})}}
    readonly_fields = ('mapa_ubicacion', 'plazos_por_revisar', 'identidad_validada_en', 'identidad_validada_por',
                       'estado_validado_en', 'estado_validado_por')
    actions = ['validar_identidad', 'validar_estado']
    fieldsets = (
        (None, {'fields': ('nombre', 'sigla', 'slug', 'area', 'estado', 'lema', 'proposito')}),
        (_('Qué es y para qué'), {'fields': ('presentacion', 'objetivo_general', 'objetivos_especificos',
                                             'cadena', 'cifras')}),
        (_('Identidad institucional'), {'fields': ('adscripcion', 'mision', 'vision', 'sectores_retos',
                                                   'fuente_identidad', 'identidad_validada_en', 'identidad_validada_por'),
                                       'description': _('Misión y visión se publican después de validar su fuente mediante la acción de la lista.')}),
        (_('Respaldo del estado'), {'fields': ('fuente_estado', 'estado_validado_en', 'estado_validado_por'),
                                   'description': _('El estado operativo requiere respaldo propio; no acredita disponibilidad de equipos ni horarios.')}),
        (_('Dónde está'), {
            'fields': ('ubicacion', 'direccion', 'mapa_ubicacion', ('latitud', 'longitud'), 'como_llegar', 'horario_atencion'),
            'description': _('Se muestra en «Ubicación y cómo llegar» de la ficha pública: marque el punto en el mapa '
                             'o escriba las coordenadas; sin punto, la ficha enseña las sedes y busca la dirección.'),
        }),
        (_('Imagen, videos y recorrido'), {'fields': ('imagen', 'credito_imagen', 'videos', 'recorrido_360_url',
                                                      'visitas_texto', 'color', 'fuente')}),
        (_('Quién responde'), {'fields': ('responsable', 'cuentas_gestoras', 'contacto_email', 'activo', 'orden')}),
    )
    inlines = [GobiernoInline, RutaInline, ModalidadInline, LineaInline, PlanoInline, ZonaInline, RelacionAreaInline,
               FaseInline, PresupuestoInline, IndicadorInline, RiesgoInline, ArticulacionInline, ImagenCentroInline,
               AjusteInline]

    def get_queryset(self, request):
        consulta = super().get_queryset(request)
        principal = principal_vigente(request.user)
        if principal is None:
            return consulta.none()
        if principal.is_superuser:
            return consulta
        return consulta.filter(models.Q(responsable_id=principal.pk) | models.Q(gestores__pk=principal.pk)).distinct()

    def has_view_permission(self, request, obj=None):
        return bool(principal_vigente(request.user) and super().has_view_permission(request, obj)
                    and (obj is None or obj.puede_gestionar(request.user)))

    def has_change_permission(self, request, obj=None):
        return bool(principal_vigente(request.user) and super().has_change_permission(request, obj)
                    and (obj is None or obj.puede_gestionar(request.user)))

    def has_add_permission(self, request):
        principal = principal_vigente(request.user)
        return bool(principal and principal.is_superuser and super().has_add_permission(request))

    def has_delete_permission(self, request, obj=None):
        principal = principal_vigente(request.user)
        return bool(principal and principal.is_superuser and super().has_delete_permission(request, obj))

    def save_model(self, request, obj, form, change):
        principal = principal_vigente(request.user)
        # Verificar la asignación persistida, no la autoridad enviada en el POST.
        anterior = self.get_queryset(request).filter(pk=obj.pk).first() if change else None
        if principal is None or (not principal.is_superuser and
                                  (anterior is None or not anterior.puede_gestionar(request.user))):
            raise PermissionDenied
        super().save_model(request, obj, form, change)

    def get_formsets_with_inlines(self, request, obj=None):
        if obj is not None and not self.has_view_permission(request, obj):
            return
        for formulario, inline in super().get_formsets_with_inlines(request, obj):
            if obj is not None:
                _acotar_campos(formulario.form, obj.pk)
            yield formulario, inline

    def get_fieldsets(self, request, obj=None):
        campos = super().get_fieldsets(request, obj)
        if obj and obj.puede_gestionar(request.user):
            return tuple(campos) + ((_('Seguimiento de gestión'), {'fields': ('plazos_por_revisar',)}),)
        return campos

    @admin.display(description=_('Plazos por revisar'))
    def plazos_por_revisar(self, obj):
        from .investigacion import alertas_del_centro

        alertas = alertas_del_centro(obj)
        if not alertas:
            return _('Sin plazos pendientes dentro del horizonte de revisión.')
        return format_html('<ul>{}</ul>', format_html_join('',
            '<li><a href="{}">{}</a> · {} · {} · {}</li>',
            ((a['url'], a['titulo'], a['contexto'], a['fecha'].strftime('%d/%m/%Y'), a['estado']) for a in alertas)))

    def _validar(self, request, consulta, metodo):
        for centro in consulta:
            try:
                getattr(centro, metodo)(request.user)
            except ValidationError as error:
                self.message_user(request, f'{centro}: {" ".join(error.messages)}', messages.WARNING)
                continue
            self.log_change(request, centro, metodo.replace('_', ' '))
            self.message_user(request, f'{centro}: validación registrada.', messages.SUCCESS)

    @admin.action(description=_('Validar identidad institucional'), permissions=['change'])
    def validar_identidad(self, request, consulta):
        self._validar(request, consulta, 'validar_identidad')

    @admin.action(description=_('Validar el estado del centro'), permissions=['change'])
    def validar_estado(self, request, consulta):
        self._validar(request, consulta, 'validar_estado')

    # El mismo mapa con el que las unidades marcan su punto (Leaflet y las sedes dibujadas), por sus rutas estáticas.
    class Media:
        css = {'all': (f"{static('js/vendor/leaflet/leaflet.css')}?v=1.9.4",
                       f"{static('portal/css/pages/unidades/mapa_unidad.css')}?v=20260928-piso-foto-v1")}
        js = (f"{static('js/vendor/leaflet/leaflet.js')}?v=1.9.4",
              f"{static('portal/js/pages/unidades/mapa_unidad.js')}?v=20260928-piso-foto-v1")

    @admin.display(description=_('Punto exacto'))
    def mapa_ubicacion(self, obj):
        from .vinculos import sedes_en_el_mapa

        return format_html(
            '<div class="mapa-unidad-editor"><div class="mapa-unidad mapa-unidad--editor" data-mapa-editor '
            'data-sedes="{}" data-unidades="[]" data-imagen="{}" data-nombre="{}"></div>'
            '<p class="mapa-unidad__ayuda">{}</p></div>',
            json.dumps(sedes_en_el_mapa()), obj.imagen.url if obj and obj.imagen else '', obj.nombre if obj else '',
            _('Toque el mapa donde está el centro o arrastre el marcador; tocar un edificio de una sede propone su '
              'nombre y su dirección.'))

    @admin.display(description=_('Área prioritaria'), ordering='area')
    def nombre_area(self, obj):
        return obj.nombre_area


class ImagenComponenteInline(_Tabla):
    model = ImagenCentro
    fk_name = 'componente'
    fields = ('imagen', 'titulo', 'credito', 'fuente', 'es_plano', 'orden')


class EquipoInline(_Tabla):
    model = EquipoCentro
    fields = ('categoria', 'nombre', 'detalle', 'funcion', 'cantidad', 'codigo', 'estado', 'imagen', 'orden')


@admin.register(Componente)
class ComponenteAdmin(_DelCentro, AdministracionTraducida):
    list_display = ('orden', 'nombre_corto', 'tipo', 'centro', 'estado', 'area_m2', 'publicado')
    list_display_links = ('nombre_corto',)
    list_filter = ('centro', 'tipo', 'estado', 'publicado')
    search_fields = ('nombre', 'nombre_corto', 'resumen')
    formfield_overrides = {TextField: {'widget': forms.Textarea(attrs={'rows': 5})}}
    fieldsets = (
        (None, {'fields': ('centro', 'tipo', 'integrado_en', 'codigo', 'nombre', 'nombre_corto', 'icono', 'color', 'resumen',
                           'descripcion', 'estado', 'publicado', 'orden')}),
        (_('Qué hace y qué entrega'), {'fields': ('funciones', 'capacidades', 'resultados', 'flujo')}),
        (_('Equipamiento, software y seguridad'), {'fields': ('equipamiento', 'software', 'seguridad')}),
        (_('Operaciones, materiales y participación académica'),
         {'fields': ('organizacion_operativa', 'insumos_materiales', 'usos_academicos')}),
        (_('Dónde está y con quién se articula'), {'fields': ('area_m2', 'nivel', 'unidades_articuladas', 'unidad_slug',
                                                              'videos', 'recorrido_360_url')}),
    )
    inlines = [EquipoInline, ImagenComponenteInline]

    def save_formset(self, request, form, formset, change):
        # Las fotos de un área pertenecen también a su centro.
        instancias = formset.save(commit=False)
        for instancia in instancias:
            if isinstance(instancia, ImagenCentro):
                instancia.centro_id = form.instance.centro_id
            instancia.save()
        for eliminada in formset.deleted_objects:
            eliminada.delete()
        formset.save_m2m()


class PasoInline(BloqueTraducido):
    model = PasoProceso
    extra = 0
    formfield_overrides = TEXTO_CORTO
    filter_horizontal = ('equipos',)
    fields = (('numero', 'nombre'), 'descripcion', 'subpasos', ('parametros', 'controles'), 'equipos')


@admin.register(ProcesoArea)
class ProcesoAreaAdmin(_DelCentro, AdministracionTraducida):
    campo_centro = 'componente__centro'
    list_display = ('nombre', 'componente', 'entrada', 'salida', 'orden', 'publicado')
    list_filter = ('componente__centro', 'componente', 'publicado')
    search_fields = ('nombre', 'descripcion')
    inlines = [PasoInline]


@admin.register(EquipoCentro)
class EquipoCentroAdmin(_ContenidoDelCentro, AdministracionTraducida):
    campo_centro = 'componente__centro'
    list_display = ('nombre', 'categoria', 'componente', 'cantidad', 'codigo', 'estado')
    list_filter = ('componente__centro', 'componente', 'estado', 'categoria')
    search_fields = ('nombre', 'categoria', 'detalle', 'funcion', 'codigo')
    list_editable = ('estado',)


@admin.register(Zona)
class ZonaAdmin(_ContenidoDelCentro, AdministracionTraducida):
    list_display = ('nombre', 'centro', 'componente', 'reservable', 'estado_acceso', 'aforo', 'margen_minutos')
    list_filter = ('centro', 'estado_acceso', 'reservable')
    search_fields = ('nombre', 'codigo', 'requisitos')
    formfield_overrides = TEXTO_CORTO


@admin.register(Servicio)
class ServicioAdmin(_DelCentro, AdministracionTraducida):
    list_display = ('nombre', 'linea', 'componente', 'entregable', 'usuarios', 'tarifa', 'activo')
    list_filter = ('centro', 'linea', 'usuarios', 'activo')
    search_fields = ('nombre', 'descripcion', 'entregable')
    list_editable = ('activo',)


@admin.register(Grupo)
class GrupoAdmin(_ContenidoDelCentro, AdministracionTraducida):
    list_display = ('nombre', 'sigla', 'facultad', 'centro', 'activo')
    list_filter = ('centro', 'activo')
    search_fields = ('nombre', 'sigla', 'descripcion')
    filter_horizontal = ('lineas',)


@admin.register(Integrante)
class IntegranteAdmin(_ContenidoDelCentro, AdministracionTraducida):
    list_display = ('nombre', 'rol', 'cargo', 'componente', 'grupo', 'centro', 'vigente')
    list_filter = ('centro', 'rol', 'componente', 'grupo', 'vigente')
    search_fields = ('nombre', 'cargo', 'perfil', 'orcid')
    filter_horizontal = ('lineas',)
    list_editable = ('vigente',)


class SesionInline(_Tabla):
    model = SesionAcompanamiento
    fields = ('responsable', 'inicio', 'fin', 'modalidad', 'estado', 'acuerdos', 'notas_internas')
    can_delete = False


class TareaInline(_Tabla):
    model = TareaSolicitud
    fields = ('titulo', 'a_cargo', 'plazo', 'completada', 'evidencia')
    can_delete = False


class HistorialInline(_Tabla):
    model = RegistroSolicitud
    fields = readonly_fields = ('fecha', 'autor', 'estado_anterior', 'estado_nuevo', 'detalle')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SolicitudCentro)
class SolicitudCentroAdmin(_DelCentro, AdministracionTraducida):
    """La bandeja del centro: cada solicitud avanza por la ruta y, si pide acceso a un área, se le confirma el horario."""
    list_display = ('creada', 'titulo', 'tipo', 'perfil', 'centro', 'estado', 'zona', 'inicio_reservado')
    list_filter = ('centro', 'estado', 'tipo', 'perfil', 'prioridad')
    search_fields = ('titulo', 'problema', 'institucion', 'usuario__username', 'usuario__email')
    date_hierarchy = 'creada'
    readonly_fields = ('usuario', 'creada', 'actualizada', 'cerrada_en')
    fieldsets = (
        (_('Lo que pidió'), {'fields': ('centro', 'usuario', 'tipo', 'perfil', 'institucion', 'titulo', 'problema',
                                        'resultado_esperado', 'servicio', 'componente', 'fecha_preferida', 'participantes',
                                        'finalidad', 'proyecto', 'desarrollo', 'equipo', 'inicio_preferido', 'fin_preferido')}),
        (_('Atención, área y horario'), {'fields': ('estado', 'prioridad', 'zona', 'inicio_reservado', 'fin_reservado',
                                                    'respuesta', 'entregable', 'requisitos_validados', 'evidencia_requisitos',
                                                    'supervisor', 'responsable_atencion', 'diagnostico', 'plan',
                                                    'evaluacion_cierre', 'notas_internas')}),
        (_('Registro'), {'fields': ('creada', 'actualizada', 'cerrada_en')}),
    )
    inlines = [SesionInline, TareaInline, HistorialInline]
    actions = ['pasar_a_evaluacion', 'aprobar', 'iniciar', 'entregar', 'cerrar', 'no_procede', 'cancelar']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('centro', 'usuario', 'zona')

    def save_model(self, request, obj, form, change):
        if change and 'estado' in form.changed_data:
            anterior = SolicitudCentro.objects.get(pk=obj.pk).estado
            nuevo = obj.estado
            obj.estado = anterior
            obj.avanzar(nuevo)
        if not obj.centro.puede_gestionar(request.user):
            raise PermissionDenied
        obj.save(actor=request.user)

    def save_formset(self, request, form, formset, change):
        for objeto in formset.save(commit=False):
            if isinstance(objeto, SesionAcompanamiento):
                objeto.save(actor=request.user)
            else:
                objeto.save()
        formset.save_m2m()

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        try:
            return super().changeform_view(request, object_id, form_url, extra_context)
        except ValidationError as error:
            self.message_user(request, ' '.join(error.messages), messages.ERROR)
            return redirect(request.path)

    def _avanzar(self, request, consulta, estado):
        hechas = 0
        for solicitud in consulta:
            try:
                solicitud.avanzar(estado)
                solicitud.full_clean()
                solicitud.save(actor=request.user)
            except ValidationError as error:
                self.message_user(request, f'{solicitud.titulo}: {" ".join(error.messages)}', messages.WARNING)
                continue
            hechas += 1
        if hechas:
            self.message_user(request, f'{hechas} solicitud(es) actualizada(s).', messages.SUCCESS)

    @admin.action(description=_('Pasar a evaluación técnica'))
    def pasar_a_evaluacion(self, request, consulta):
        self._avanzar(request, consulta, 'evaluacion')

    @admin.action(description=_('Aprobar y planificar'))
    def aprobar(self, request, consulta):
        self._avanzar(request, consulta, 'aprobada')

    @admin.action(description=_('Iniciar la ejecución'))
    def iniciar(self, request, consulta):
        self._avanzar(request, consulta, 'ejecucion')

    @admin.action(description=_('Marcar como entregada'))
    def entregar(self, request, consulta):
        self._avanzar(request, consulta, 'entregada')

    @admin.action(description=_('Cerrar'))
    def cerrar(self, request, consulta):
        self._avanzar(request, consulta, 'cerrada')

    @admin.action(description=_('No procede'))
    def no_procede(self, request, consulta):
        self._avanzar(request, consulta, 'no_procede')


    @admin.action(description=_('Cancelar conservando el expediente'))
    def cancelar(self, request, consulta):
        self._avanzar(request, consulta, 'cancelada')


class HitoInline(_Tabla):
    model = HitoProyecto
    fields = ('titulo', 'fecha_prevista', 'estado', 'fecha_cumplida', 'evidencia', 'publico')


@admin.register(LineaInvestigacion)
class LineaInvestigacionAdmin(_DelCentro, AdministracionTraducida):
    list_display = ('nombre', 'centro', 'ambito', 'responsable', 'componente')
    list_filter = ('centro', 'componente')
    search_fields = ('nombre', 'problema', 'objetivos', 'preguntas')


@admin.register(Proyecto)
class ProyectoAdmin(_ContenidoDelCentro, AdministracionTraducida):
    list_display = ('titulo', 'centro', 'estado', 'etapa', 'avance', 'financiador', 'inicio', 'fin', 'destacado',
                    'publicado')
    list_filter = ('centro', 'estado', 'etapa', 'linea', 'destacado', 'publicado')
    search_fields = ('titulo', 'codigo', 'resumen', 'financiador')
    filter_horizontal = ('componentes', 'equipo', 'aliados')
    inlines = [HitoInline]
    fieldsets = (
        (None, {'fields': ('centro', 'codigo', 'titulo', 'resumen', 'linea', 'componentes', 'categoria', 'sector', 'estado', 'etapa')}),
        (_('Problema y método'), {'fields': ('problema', 'objetivos', 'metodologia')}),
        (_('Avance respaldado'), {'fields': ('avance', 'avance_metodo', 'avance_fecha', 'avance_evidencia'),
                                 'description': _('El porcentaje se muestra al público solo con método, fecha y evidencia.')}),
        (_('Equipo y financiamiento'), {'fields': ('responsable', 'equipo', 'investigadores', 'financiador', 'monto',
                                                  'aliados', 'monto_publico')}),
        (_('Fechas, hitos y difusión'), {'fields': ('inicio', 'fin', 'hitos', 'enlace', 'imagen', 'destacado',
                                                    'publicado')}),
        (_('Procedencia'), {'fields': ('es_muestra', 'fuente_validacion', 'validado_en', 'validado_por')}),
    )


@admin.register(Resultado)
class ResultadoAdmin(_ContenidoDelCentro, AdministracionTraducida):
    list_display = ('titulo', 'tipo', 'anio', 'revista', 'cuartil', 'trl', 'proyecto', 'centro', 'confidencial', 'publicado')
    list_filter = ('centro', 'tipo', 'anio', 'acceso', 'cuartil', 'confidencial', 'publicado')
    search_fields = ('titulo', 'doi', 'revista', 'autores_texto', 'descripcion')
    filter_horizontal = ('autores',)


@admin.register(CasoExito)
class CasoExitoAdmin(_ContenidoDelCentro, AdministracionTraducida):
    list_display = ('titulo', 'beneficiario', 'sector', 'anio', 'componente', 'centro', 'publicado')
    list_filter = ('centro', 'sector', 'anio', 'publicado')
    search_fields = ('titulo', 'beneficiario', 'reto', 'solucion', 'resultado')


@admin.register(Aliado)
class AliadoAdmin(_ContenidoDelCentro, AdministracionTraducida):
    list_display = ('nombre', 'tipo', 'pais', 'convenio', 'vigencia_hasta', 'centro', 'activo')
    list_filter = ('centro', 'tipo', 'activo')
    search_fields = ('nombre', 'aporte', 'convenio')


@admin.register(Convocatoria)
class ConvocatoriaAdmin(_ContenidoDelCentro, AdministracionTraducida):
    list_display = ('titulo', 'tipo', 'componente', 'cierre', 'centro', 'activa')
    list_filter = ('centro', 'tipo', 'activa')
    search_fields = ('titulo', 'descripcion')
    list_editable = ('activa',)


@admin.register(Novedad)
class NovedadAdmin(_ContenidoDelCentro, AdministracionTraducida):
    list_display = ('fecha', 'titulo', 'tipo', 'lugar', 'centro', 'publicada')
    list_filter = ('centro', 'tipo', 'publicada')
    search_fields = ('titulo', 'resumen')
    date_hierarchy = 'fecha'


@admin.register(DocumentoCentro)
class DocumentoCentroAdmin(_ContenidoDelCentro, AdministracionTraducida):
    list_display = ('titulo', 'tipo', 'estado_documental', 'emisor', 'version', 'periodo', 'fecha', 'centro', 'publico')
    list_filter = ('centro', 'tipo', 'estado_documental', 'publico')
    search_fields = ('titulo', 'resumen')


class RecursoInline(_Tabla):
    model = RecursoCentro
    fields = ('tipo', 'titulo', 'descripcion', 'archivo', 'url', 'texto', 'orden', 'activo')


@admin.register(CarpetaCentro)
class CarpetaCentroAdmin(_DelCentro, AdministracionTraducida):
    list_display = ('nombre', 'pestana', 'seccion', 'visibilidad', 'centro', 'orden', 'activa')
    list_filter = ('centro', 'pestana', 'visibilidad', 'activa')
    search_fields = ('nombre', 'descripcion')
    inlines = [RecursoInline]


@admin.register(HorarioRecurso, BloqueoRecurso)
class AgendaRecursoAdmin(_DelCentro, AdministracionTraducida):
    list_filter = ('centro',)


@admin.register(HabilitacionEquipo)
class HabilitacionEquipoAdmin(_DelCentro, AdministracionTraducida):
    campo_centro = 'equipo__componente__centro'
    list_display = ('equipo', 'usuario', 'desde', 'hasta', 'verificador', 'revocada')
    list_filter = ('revocada', 'equipo__componente__centro')
    readonly_fields = ('verificador',)

    def save_model(self, request, obj, form, change):
        obj.verificador = identidad_de(request.user)
        obj.full_clean()
        super().save_model(request, obj, form, change)


@admin.register(HerramientaCentro)
class HerramientaCentroAdmin(_DelCentro, AdministracionTraducida):
    list_display = ('nombre', 'centro', 'tipo', 'version', 'publicado', 'validado_en')
    list_filter = ('centro', 'tipo', 'publicado')
    readonly_fields = ('validado_en', 'validado_por')
    actions = ['validar_herramienta']

    @admin.action(description=_('Validar método, versión y condiciones de la herramienta'))
    def validar_herramienta(self, request, consulta):
        for herramienta in consulta:
            try:
                herramienta.validar(request.user)
            except ValidationError as error:
                self.message_user(request, ' '.join(error.messages), messages.WARNING)
