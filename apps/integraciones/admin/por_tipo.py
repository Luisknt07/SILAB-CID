"""Paneles acotados a un tipo de unidad.

Un expediente (reserva, consumible, orden de producción) pertenece a una
unidad, y la unidad a un tipo. La sección de un tipo solo ve lo de sus
unidades, y al crear un registro solo ofrece esas unidades. Nada de esto
cambia el panel heredado: se hereda y se recorta.
"""

from django.contrib.admin.options import IS_POPUP_VAR, TO_FIELD_VAR
from django.core.exceptions import PermissionDenied
from django.db import models
from django.template.response import TemplateResponse
from django.urls import reverse

from apps.core.presentation.tipologias import codigos_por_base

# Parametro de lista que obliga a mostrar todas las unidades juntas.
TODAS = 'todas'


def ruta_a_la_unidad(modelo, profundidad=0):
    """Campo (o cadena de campos) que lleva del modelo a su unidad, o None.

    Primero por claves foraneas propias; si el modelo no apunta a nadie (una
    ficha tecnica de equipo), por la relacion inversa de quien lo asigna a
    una unidad.
    """
    from apps.directorio_unidades.models.core import Unidad

    if profundidad > 2:
        return None
    relaciones = [campo for campo in modelo._meta.get_fields()
                  if isinstance(campo, (models.ForeignKey, models.OneToOneField))]
    for campo in relaciones:
        if campo.related_model is Unidad:
            return campo.name
    for campo in relaciones:
        if campo.related_model is modelo or campo.related_model is None:
            continue
        resto = ruta_a_la_unidad(campo.related_model, profundidad + 1)
        if resto:
            return f'{campo.name}__{resto}'
    if profundidad == 0:
        for inversa in modelo._meta.get_fields():
            if not isinstance(inversa, models.ManyToOneRel) or inversa.related_model is modelo:
                continue
            resto = ruta_a_la_unidad(inversa.related_model, profundidad + 1)
            if resto:
                return f'{inversa.name}__{resto}'
    return None


def ruta_es_inversa(modelo, ruta):
    """True si el primer tramo de la ruta es una relacion inversa del modelo."""
    primero = ruta.partition('__')[0]
    return isinstance(modelo._meta.get_field(primero), models.ManyToOneRel)


class AcotadoPorTipologia:
    """Mezcla para un ModelAdmin: solo las filas de las unidades de un tipo."""

    base_tipologia = ''
    ruta = 'unidad'
    ruta_inversa = False

    def codigos(self):
        return codigos_por_base(self.base_tipologia)

    def get_queryset(self, request):
        consulta = super().get_queryset(request)
        propio = models.Q(**{f'{self.ruta}__dependencia__in': self.codigos()})
        if not self.ruta_inversa:
            return consulta.filter(propio)
        # Por relacion inversa una fila puede repetirse (un equipo compartido
        # por tres unidades) y una ficha recien creada aun no tiene unidad:
        # se muestra hasta que alguien la asigne.
        sin_asignar = models.Q(**{f'{self.ruta}__isnull': True})
        return consulta.filter(propio | sin_asignar).distinct()

    @property
    def parametro_unidad(self):
        return f'{self.ruta}__id__exact'

    @property
    def parametro_sin_asignar(self):
        return f'{self.ruta}__isnull'

    def lookup_allowed(self, lookup, value, request=None):
        # La puerta por unidad filtra por la ruta hasta la unidad, tambien
        # cuando es inversa y el panel heredado no la declara como filtro.
        if lookup in (self.parametro_unidad, self.parametro_sin_asignar):
            return True
        return super().lookup_allowed(lookup, value, request)

    def changelist_view(self, request, extra_context=None):
        if self._pide_elegir_unidad(request):
            return self._elegir_unidad(request)
        if TODAS in request.GET:
            # Django rechaza parametros que no filtran nada; este ya cumplio.
            request.GET = request.GET.copy()
            del request.GET[TODAS]
        return super().changelist_view(request, extra_context)

    def _pide_elegir_unidad(self, request):
        """Sin unidad elegida, sin busqueda y sin pedir todas: se elige primero."""
        if request.method != 'GET' or not self.ruta:
            return False
        atajos = {self.parametro_unidad, self.parametro_sin_asignar, 'q', TODAS,
                  IS_POPUP_VAR, TO_FIELD_VAR}
        return not (set(request.GET) & atajos)

    def _elegir_unidad(self, request):
        """Una fila por unidad del tipo con cuantos registros tiene aqui."""
        from apps.directorio_unidades.models.core import Unidad

        if not self.has_view_or_change_permission(request):
            raise PermissionDenied
        propios = self.get_queryset(request).filter(
            **{f'{self.ruta}__dependencia__in': self.codigos()})
        conteo = dict(propios.values_list(self.ruta).annotate(n=models.Count('pk', distinct=True))
                      .values_list(self.ruta, 'n'))
        visibles = Unidad.objects.filter(dependencia__in=self.codigos())
        if getattr(self, '_local', lambda r: False)(request):
            visibles = visibles.filter(pk__in=self._unidades(request))
        if self.model._meta.concrete_model.__name__ in ('DocumentoExpediente', 'DocumentoElaborado'):
            from apps.gestion_unidades.presentation.permisos import unidades_del_expediente
            visibles = visibles.filter(pk__in=unidades_del_expediente(request.user))
        unidades = [{
            'unidad': unidad, 'total': conteo.get(unidad.pk, 0),
            'url': f'?{self.parametro_unidad}={unidad.pk}',
        } for unidad in visibles.order_by('nombre')]
        sin_asignar = None
        if self.ruta_inversa and not getattr(self, '_local', lambda r: False)(request):
            sueltos = self.model._default_manager.filter(**{self.parametro_sin_asignar: True}).count()
            if sueltos:
                sin_asignar = {'total': sueltos, 'url': f'?{self.parametro_sin_asignar}=True'}
        contexto = {
            **self.admin_site.each_context(request),
            'opts': self.opts,
            'title': str(self.opts.verbose_name_plural),
            'unidades': unidades,
            'sin_asignar': sin_asignar,
            'total': sum(conteo.values()) + (sin_asignar['total'] if sin_asignar else 0),
            'add_url': reverse(f'admin:{self.opts.app_label}_{self.opts.model_name}_add')
            if self.has_add_permission(request) else '',
        }
        return TemplateResponse(request, 'admin/por_tipo/elegir_unidad.html', contexto)

    def get_urls(self):
        """Las rutas propias del panel heredado cambian de nombre en cada seccion.

        `reservas-estadisticas` existe una vez por seccion; si conservara el
        nombre, `reverse` apuntaria a la ultima registrada y los reportes del
        panel general abririan acotados a un tipo. Las rutas estandar ya
        llevan el prefijo de la seccion y no se tocan.
        """
        rutas = super().get_urls()
        prefijo = f'{self.opts.app_label}_{self.opts.model_name}_'
        for ruta in rutas:
            if ruta.name and not ruta.name.startswith(prefijo):
                ruta.name = f'{self.opts.app_label}-{ruta.name}'
        return rutas

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        campo = super().formfield_for_foreignkey(db_field, request, **kwargs)
        primero, _, resto = self.ruta.partition('__')
        if campo is not None and db_field.name == primero:
            # Se recorta despues del panel heredado: si este ya acoto el
            # selector, aqui solo se estrecha mas, nunca se ensancha.
            filtro = f'{resto}__dependencia__in' if resto else 'dependencia__in'
            campo.queryset = campo.queryset.filter(**{filtro: self.codigos()})
        return campo


def panel_acotado(panel_heredado, modelo, base_tipologia):
    """Subclase del panel heredado recortada al tipo de unidad de `modelo`."""
    from apps.gestion_unidades.admin.alcance_unidad import AlcanceUnidadAdmin
    ruta = ruta_a_la_unidad(modelo)
    return type(f'{modelo.__name__}Por{base_tipologia.title().replace("_", "")}Admin',
                (AlcanceUnidadAdmin, AcotadoPorTipologia, panel_heredado),
                {'base_tipologia': base_tipologia, 'ruta': ruta,
                 'ruta_inversa': ruta_es_inversa(modelo, ruta)})
