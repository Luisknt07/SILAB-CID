"""Edición de referencias comerciales sin cambiar la identidad ni las existencias."""
from copy import deepcopy

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.recursos.models.medios import medios_publicos, validar_medios_referencia


IDENTIDAD = ('marca', 'modelo', 'sku', 'variante', 'presentacion')
CAMPOS_REFERENCIA = tuple('referencia_' + campo for campo in IDENTIDAD) + ('referencia_descripcion',)
ROTULOS = {
    'marca': 'Marca de referencia', 'modelo': 'Modelo o producto de referencia',
    'sku': 'SKU o código comercial de referencia', 'variante': 'Variante de referencia',
    'presentacion': 'Presentación de referencia',
}


def firma_video(video):
    """Una edición manual del video rompe su antigua firma y obliga a revisarlo."""
    return {'id': video.pk, 'url': video.url, 'titulo': video.titulo, 'canal': video.canal}


def videos_vigentes(tipo):
    """Conserva los registros anteriores, sin atribuirlos a otro producto."""
    propios = list(tipo.videos.all())
    candidatos = propios or (list(tipo.familia.videos.all()) if tipo.familia_id else [])
    medios = medios_publicos(getattr(tipo, 'medios_referencia', {}))
    pendientes = medios.get('videos_por_revisar', [])
    if not isinstance(pendientes, list):
        pendientes = []
    # Elegir la familia antes de filtrar evita publicar de pronto otro conjunto
    # de videos cuando todos los del modelo están pendientes de comprobación.
    return [video for video in candidatos if firma_video(video) not in pendientes]


class ReferenciaComercialMixin:
    """Seis campos legibles; el JSON y el inventario nunca se editan directamente."""

    def __init__(self, *args, referencia_request=None, referencia_unidad=None,
                 habilitar_referencia=True, **kwargs):
        self.referencia_request = referencia_request
        self.referencia_unidad = referencia_unidad
        self.referencia_editable = False
        self.referencia_nombres = ()
        self._plan_referencia = None
        self._referencia_preparada = False
        self._referencia_auditada = False
        super().__init__(*args, **kwargs)
        actual = medios_publicos(getattr(self.instance, 'medios_referencia', {}))
        if not habilitar_referencia or actual.get('estado') not in (
                'referencia_provisional', 'documentado_por_confirmar'):
            return
        self.referencia_editable = True
        self.referencia_nombres = CAMPOS_REFERENCIA + ('referencia_presente',)
        self._referencia_anterior = deepcopy(self.instance.medios_referencia)
        propuesta = actual.get('identidad_propuesta', {})
        # Los formularios abiertos antes de añadir estos campos siguen guardando
        # sus propios datos, sin borrar ni invalidar la referencia por omisión.
        self._referencia_enviada = self.is_bound and any(
            self.add_prefix(campo) in self.data for campo in self.referencia_nombres)
        for clave in IDENTIDAD:
            nombre = 'referencia_' + clave
            self.fields[nombre] = forms.CharField(
                label=ROTULOS[clave], max_length=300, required=False,
                help_text='Ejemplo comercial por confirmar; no cambia la identidad del bien registrado.')
            self.initial[nombre] = propuesta.get(clave, '')
        self.fields['referencia_descripcion'] = forms.CharField(
            label='Descripción del producto de referencia', required=False, max_length=2000,
            widget=forms.Textarea(attrs={'rows': 3}),
            help_text='Describe la nueva referencia. Si cambia el producto y no revisas este texto, se retira la descripción anterior.')
        self.initial['referencia_descripcion'] = actual.get('descripcion_referencia', '')
        self.fields['referencia_presente'] = forms.CharField(required=False, widget=forms.HiddenInput)
        self.initial['referencia_presente'] = '1'

    @property
    def referencia_campos(self):
        return [self[nombre] for nombre in CAMPOS_REFERENCIA if nombre in self.fields]

    @property
    def referencia_identidad_cambiada(self):
        return bool(self._plan_referencia and self._plan_referencia['identidad_cambiada'])

    def clean(self):
        datos = super().clean()
        if not self.referencia_editable or not self._referencia_enviada:
            return datos
        anterior = self._referencia_anterior
        identidad = {clave: datos.get('referencia_' + clave, '') for clave in IDENTIDAD}
        identidad = {clave: valor for clave, valor in identidad.items() if valor}
        previa = anterior.get('identidad_propuesta', {})
        cambio_identidad = any(identidad.get(campo, '') != previa.get(campo, '') for campo in IDENTIDAD)
        if identidad or anterior.get('estado') == 'referencia_provisional':
            for campo in ('marca', 'modelo'):
                if not identidad.get(campo) and 'referencia_' + campo not in self.errors:
                    self.add_error('referencia_' + campo, 'Completa la marca y el modelo de la referencia comercial.')
        if any(nombre in self.errors for nombre in CAMPOS_REFERENCIA):
            return datos
        descripcion = datos.get('referencia_descripcion', '')
        if cambio_identidad and descripcion == anterior.get('descripcion_referencia', ''):
            descripcion = ''
        nuevo = deepcopy(anterior)
        nuevo['identidad_propuesta'] = identidad
        nuevo['descripcion_referencia'] = descripcion
        if cambio_identidad:
            nuevo['estado'] = 'referencia_provisional' if identidad else 'documentado_por_confirmar'
            nuevo['identidad'] = ' '.join(filter(None, (identidad.get('marca'), identidad.get('modelo'))))
            nuevo['medios_por_revisar'] = True
            nuevo['imagen'], nuevo['documentos'], nuevo['videos'] = {}, [], []
            nuevo['limite'] = ('Referencia comercial revisada por la unidad. Las imágenes y los enlaces del producto '
                              'anterior se conservan en el historial y requieren revisión antes de volver a publicarse. '
                              'Confirmar la identidad del activo físico por separado.')
        try:
            validar_medios_referencia(nuevo)
        except ValidationError as error:
            self.add_error(None, error)
            return datos
        if nuevo != anterior:
            self._plan_referencia = {'nuevo': nuevo, 'identidad_cambiada': cambio_identidad}
        return datos

    def aplicar_referencia(self, objeto):
        if self._plan_referencia is None:
            return
        nuevo = deepcopy(self._plan_referencia['nuevo'])
        if not self._referencia_preparada:
            self._referencia_catalogo = {}
            if self._plan_referencia['identidad_cambiada']:
                campos = ('logo_catalogo',) if hasattr(objeto, 'logo_catalogo') else (
                    'imagen_catalogo', 'fuente_imagen', 'credito_imagen')
                self._referencia_catalogo = {campo: getattr(objeto, campo, '') for campo in campos}
                fuente = self._referencia_anterior.get('imagen', {}).get('fuente')
                if len(campos) > 1 and fuente and fuente == self._referencia_catalogo[campos[1]]:
                    for campo in campos:
                        setattr(objeto, campo, '')
                pendientes = deepcopy(self._referencia_anterior.get('videos_por_revisar', []))
                if hasattr(objeto, 'videos') and objeto.pk:
                    propios = list(objeto.videos.all())
                    candidatos = propios or (list(objeto.familia.videos.all()) if objeto.familia_id else [])
                    for video in candidatos:
                        firma = firma_video(video)
                        if firma not in pendientes:
                            pendientes.append(firma)
                nuevo['videos_por_revisar'] = pendientes
            nuevo['referencia_anterior'] = {
                'fecha': timezone.now().isoformat(),
                'datos': {clave: deepcopy(valor) for clave, valor in self._referencia_anterior.items()
                          if clave != 'referencia_anterior'},
                'catalogo': deepcopy(self._referencia_catalogo),
            }
            self._referencia_preparada = True
            self._plan_referencia['nuevo'] = deepcopy(nuevo)
        objeto.medios_referencia = nuevo
        # El nombre comercial de referencia ya existente en la ficha técnica
        # acompaña la propuesta, sin tocar ningún levantamiento medido.
        if (self._plan_referencia['identidad_cambiada'] and hasattr(objeto, 'especificaciones')
                and getattr(objeto, 'origen_datos_tecnicos', '') != 'medido'
                and isinstance(objeto.especificaciones, dict)):
            for clave in list(objeto.especificaciones):
                if clave.casefold() == 'modelo de referencia':
                    objeto.especificaciones = deepcopy(objeto.especificaciones)
                    objeto.especificaciones[clave] = nuevo.get('identidad', '')

    def auditar_referencia(self, objeto):
        if self._plan_referencia is None or self._referencia_auditada or self.referencia_unidad is None:
            return
        from apps.gestion_unidades.presentation.auditoria import registrar_auditoria

        registrar_auditoria(self.referencia_request, unidad=self.referencia_unidad, accion='actualizar', objeto=objeto,
            descripcion='Referencia comercial revisada sin modificar la identidad física ni las existencias',
            anteriores={'medios_referencia': self._referencia_anterior, 'catalogo': self._referencia_catalogo},
            nuevos={'medios_referencia': objeto.medios_referencia})
        self._referencia_auditada = True

    def save(self, commit=True):
        objeto = super().save(commit=False)
        self.aplicar_referencia(objeto)
        if commit:
            with transaction.atomic():
                objeto.save()
                self._save_m2m()
                self.auditar_referencia(objeto)
        return objeto


class ReferenciaComercialForm(ReferenciaComercialMixin, forms.ModelForm):
    pass
