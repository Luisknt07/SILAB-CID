"""Registro y funcionamiento de los Centros de Investigación y Desarrollo.

Un Centro I+D no es una unidad del directorio ni un laboratorio grande: sostiene una agenda de investigación aplicada,
desarrollo experimental, innovación y transferencia, con personas, proyectos, resultados y capacidades propias o
vinculadas (Reglamento UPEC 2026, art. 4 c y 20). Su ficha pública se arma desde estos registros: las áreas con sus
procesos y equipos, el equipo humano, los proyectos y su producción, la innovación y el impacto, los servicios y las
oportunidades. Lo que el centro no registra no se muestra.

Por eso vive en sus propias tablas y no como una tipología de `Unidad`: no comparte su agenda, sus reservas ni su
inventario. Los laboratorios, plantas piloto y centros experimentales con los que se articula se nombran por su
identificador público y se resuelven con el contrato del directorio, sin claves foráneas hacia el legado.
"""

import re
import unicodedata
from urllib.parse import quote, unquote

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .identidades import GestorIdentidades, GestoresCampo, ReferenciaCuenta, alias_centros, identidad_de, principal_vigente
from .areas import area as area_prioritaria
from .areas import opciones_areas
from .texto import lineas_de, pares_de, ternas_de


def normalizar_doi(valor):
    texto = valor.strip()
    if re.match(r'^https?://(?:dx[.])?doi[.]org/', texto, flags=re.I):
        texto = unquote(re.sub(r'^https?://(?:dx[.])?doi[.]org/', '', texto, flags=re.I))
    else:
        texto = re.sub(r'^doi:\s*', '', texto, flags=re.I)
    # DOI Handbook 2025, 4.3.4: equivalencia solo de A-Z; no normalizar Unicode.
    return texto.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))


def _videos_de(texto):
    videos = []
    for linea in lineas_de(texto):
        identificador, titulo, canal, descripcion = (linea.split('|') + ['', '', ''])[:4]
        if identificador.strip():
            videos.append({'id': identificador.strip(), 'titulo': titulo.strip(), 'canal': canal.strip(),
                           'descripcion': descripcion.strip()})
    return videos


class CuentaCentro(models.Model):
    """Proyección de presentación; no autentica ni concede permisos de plataforma."""
    id = models.IntegerField(primary_key=True, validators=[MinValueValidator(1)])
    username = models.CharField(_('Nombre de usuario'), max_length=150, db_index=True)
    first_name = models.CharField(_('Nombres'), max_length=150, blank=True)
    last_name = models.CharField(_('Apellidos'), max_length=150, blank=True)
    email = models.EmailField(_('Correo'), blank=True)
    is_active = models.BooleanField(_('Cuenta activa al sincronizar'), default=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Identidad del centro')
        verbose_name_plural = _('Identidades del centro')
        ordering = ('username', 'pk')

    def __str__(self):
        return self.username

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_short_name(self):
        return self.first_name

    def get_username(self):
        return self.username


class ContenidoCentro(models.Model):
    """Procedencia de los registros que pueden cargarse como ejemplos de trabajo."""
    objects = GestorIdentidades()
    es_muestra = models.BooleanField(_('Contenido demostrativo'), default=False, db_index=True,
                                     help_text=_('Los ejemplos no se publican ni cuentan como evidencia institucional.'))
    fuente_validacion = models.CharField(_('Fuente de validación institucional'), max_length=500, blank=True,
                                         help_text=_('Documento o registro real que respalda este contenido.'))
    validado_en = models.DateTimeField(_('Validado el'), null=True, blank=True, editable=False)
    validado_por = ReferenciaCuenta(CuentaCentro, on_delete=models.PROTECT, null=True, blank=True,
                                     editable=False, related_name='centros_id_%(class)s_validados',
                                     verbose_name=_('Validado por'))

    class Meta:
        abstract = True

    def validar(self, usuario):
        if not self.centro.puede_gestionar(usuario):
            raise ValidationError(_('No tiene autorización para validar contenido de este centro.'))
        if not self.fuente_validacion.strip():
            raise ValidationError(_('Registre una fuente institucional antes de validar el contenido.'))
        self.full_clean()
        self.es_muestra = False
        self.validado_en = timezone.now()
        self.validado_por = identidad_de(usuario)
        self.save()


class CentroID(models.Model):
    objects = GestorIdentidades()
    ESTADOS = [
        ('propuesta', _('Proyecto de factibilidad')),
        ('implementacion', _('En implementación')),
        ('operativo', _('Operativo')),
    ]

    nombre = models.CharField(_('Nombre'), max_length=160)
    sigla = models.CharField(_('Sigla'), max_length=20, blank=True)
    slug = models.SlugField(_('Identificador público'), max_length=160, unique=True)
    area = models.CharField(_('Área prioritaria'), max_length=30, choices=opciones_areas())
    proposito = models.TextField(
        _('Propósito'),
        help_text=_('Qué problema atiende el centro y con qué capacidades responde.'),
    )
    estado = models.CharField(_('Estado'), max_length=16, choices=ESTADOS, default='operativo')
    lema = models.CharField(_('Lema'), max_length=200, blank=True,
                            help_text=_('Una frase que diga qué hace el centro; va en la portada y en la tarjeta.'))
    presentacion = models.TextField(_('Qué es el centro'), blank=True)
    adscripcion = models.CharField(_('Adscripción institucional'), max_length=200, blank=True)
    mision = models.TextField(_('Misión oficial'), blank=True)
    vision = models.TextField(_('Visión oficial'), blank=True)
    sectores_retos = models.TextField(_('Sectores y retos que atiende'), blank=True,
                                      help_text=_('Una fila por sector: sector | reto o necesidad | destinatarios.'))
    fuente_identidad = models.CharField(_('Respaldo de la identidad oficial'), max_length=500, blank=True)
    identidad_validada_en = models.DateTimeField(_('Identidad validada el'), null=True, blank=True, editable=False)
    identidad_validada_por = ReferenciaCuenta(CuentaCentro, on_delete=models.PROTECT, null=True,
                                               blank=True, editable=False, related_name='identidades_centros_validadas')
    fuente_estado = models.CharField(_('Respaldo del estado del centro'), max_length=500, blank=True,
                                     help_text=_('Documento que acredita el estado declarado, distinto de la disponibilidad.'))
    estado_validado_en = models.DateTimeField(_('Estado validado el'), null=True, blank=True, editable=False)
    estado_validado_por = ReferenciaCuenta(CuentaCentro, on_delete=models.PROTECT, null=True,
                                            blank=True, editable=False, related_name='estados_centros_validados')
    objetivo_general = models.TextField(_('Objetivo general'), blank=True)
    objetivos_especificos = models.TextField(_('Objetivos específicos'), blank=True, help_text=_('Uno por línea.'))
    cadena = models.TextField(
        _('Cadena integrada'), blank=True,
        help_text=_('Cómo viaja un producto o un prototipo por el centro, «Etapa | área responsable | resultado».'))
    cifras = models.TextField(
        _('Cifras clave'), blank=True,
        help_text=_('Una por línea, «valor | qué mide» (superficie, inversión, plazas…); las demás se calculan solas.'))
    ubicacion = models.CharField(_('Ubicación'), max_length=200, blank=True,
                                 help_text=_('Dónde está, en palabras: campus, edificio o referencia.'))
    direccion = models.CharField(_('Dirección'), max_length=200, blank=True,
                                 help_text=_('Calle y ciudad; con ella se busca el centro mientras no tenga punto exacto.'))
    # Grados decimales (WGS84): seis decimales ubican el punto a unos 10 cm.
    latitud = models.DecimalField(_('Latitud'), max_digits=9, decimal_places=6, null=True, blank=True,
                                  validators=[MinValueValidator(-90), MaxValueValidator(90)],
                                  help_text=_('Se fija marcando el punto en el mapa del administrador.'))
    longitud = models.DecimalField(_('Longitud'), max_digits=9, decimal_places=6, null=True, blank=True,
                                   validators=[MinValueValidator(-180), MaxValueValidator(180)],
                                   help_text=_('Se fija marcando el punto en el mapa del administrador.'))
    como_llegar = models.TextField(_('Cómo llegar'), blank=True,
                                   help_text=_('Indicaciones para quien visita: por dónde entrar, transporte, parqueo.'))
    horario_atencion = models.CharField(_('Horario de atención'), max_length=120, blank=True)
    fuente = models.CharField(_('Documento de respaldo'), max_length=255, blank=True,
                              help_text=_('De dónde salen los datos publicados, por ejemplo el proyecto de factibilidad.'))
    color = models.CharField(_('Color'), max_length=7, default='#1d5b3a',
                             help_text=_('Color del botón y los acentos del centro, en hexadecimal.'))
    imagen = models.ImageField(_('Foto de portada'), upload_to='centros_id/portadas/', blank=True)
    credito_imagen = models.CharField(_('Crédito de la foto'), max_length=200, blank=True)
    videos = models.TextField(_('Videos'), blank=True,
                              help_text=_('Uno por línea, «ID de YouTube | título | canal | qué muestra».'))
    recorrido_360_url = models.URLField(
        _('Recorrido virtual'), blank=True,
        help_text=_('Enlace del recorrido 360° del edificio (Matterport, Kuula u otro que se pueda insertar).'))
    visitas_texto = models.TextField(
        _('Visitas y recorridos'), blank=True,
        help_text=_('Qué se recorre, para quién y en qué condiciones; vacío si el centro no recibe visitas.'))
    responsable = ReferenciaCuenta(
        CuentaCentro, on_delete=models.PROTECT, null=True, blank=True,
        related_name='centros_id_a_cargo', verbose_name=_('Responsable'),
    )
    gestores = GestoresCampo(
        CuentaCentro, through='GestorCentro', blank=True, related_name='centros_id_gestionados', verbose_name=_('Gestores'),
        help_text=_('Personas que atienden las solicitudes y reservas del centro, además de su responsable.'))
    contacto_email = models.EmailField(_('Correo de contacto'), blank=True)
    activo = models.BooleanField(
        _('Activo'), default=True,
        help_text=_('Un centro inactivo deja de aparecer en el portal; sus datos se conservan.'),
    )
    orden = models.PositiveSmallIntegerField(_('Orden'), default=100)
    creado_en = models.DateTimeField(_('Creado'), auto_now_add=True)

    class Meta:
        verbose_name = _('Centro I+D')
        verbose_name_plural = _('Centros I+D')
        ordering = ('orden', 'nombre')

    def __str__(self):
        return f'{self.sigla} · {self.nombre}' if self.sigla else self.nombre

    @property
    def area_prioritaria(self):
        """Área del catálogo, o None si el código guardado ya no existe."""
        return area_prioritaria(self.area)

    @property
    def nombre_area(self):
        actual = self.area_prioritaria
        return actual.nombre if actual else self.area

    @property
    def icono(self):
        actual = self.area_prioritaria
        return actual.icono if actual else 'iconsminds-building'

    lista_objetivos = property(lambda self: lineas_de(self.objetivos_especificos))
    lista_sectores_retos = property(lambda self: ternas_de(self.sectores_retos))
    lista_cifras = property(lambda self: pares_de(self.cifras))
    etapas_cadena = property(lambda self: ternas_de(self.cadena))
    lista_videos = property(lambda self: _videos_de(self.videos))

    @property
    def en_operacion(self):
        return self.estado == 'operativo'

    @property
    def tiene_coordenadas(self):
        return self.latitud is not None and self.longitud is not None

    @property
    def punto(self):
        """[latitud, longitud] para el mapa, o None."""
        return [float(self.latitud), float(self.longitud)] if self.tiene_coordenadas else None

    def clean(self):
        super().clean()
        if (self.latitud is None) != (self.longitud is None):
            raise ValidationError({'latitud' if self.latitud is None else 'longitud':
                                   _('La ubicación exacta necesita latitud y longitud; márquela en el mapa.')})

    @property
    def identidad_validada(self):
        return bool(self.identidad_validada_en and self.fuente_identidad.strip()
                    and self.adscripcion.strip() and self.mision.strip() and self.vision.strip())

    @property
    def estado_validado(self):
        return bool(self.estado_validado_en and self.fuente_estado.strip())

    @property
    def estado_publico(self):
        return self.get_estado_display() if self.estado_validado or self.en_escenario else _('Estado pendiente de validación')

    @property
    def en_escenario(self):
        from .escenarios import escenario_activo
        return escenario_activo(self)

    def validar_identidad(self, usuario):
        if not self.puede_gestionar(usuario):
            raise ValidationError(_('No tiene autorización para validar este centro.'))
        if not all((self.adscripcion.strip(), self.mision.strip(), self.vision.strip(), self.fuente_identidad.strip())):
            raise ValidationError(_('Complete adscripción, misión, visión y respaldo institucional antes de validar.'))
        self.full_clean()
        self.identidad_validada_en, self.identidad_validada_por = timezone.now(), identidad_de(usuario)
        self.save()

    def validar_estado(self, usuario):
        if not self.puede_gestionar(usuario):
            raise ValidationError(_('No tiene autorización para validar este centro.'))
        if not self.fuente_estado.strip():
            raise ValidationError(_('Registre el respaldo institucional del estado antes de validarlo.'))
        self.full_clean()
        self.estado_validado_en, self.estado_validado_por = timezone.now(), usuario
        self.save()

    def save(self, *args, **kwargs):
        # Una corrección del contenido o su fuente requiere una nueva validación; una recarga no la acredita.
        invalidados = []
        if not self._state.adding:
            anterior = type(self).objects.get(pk=self.pk)
            grupos = ((('adscripcion', 'mision', 'vision', 'sectores_retos', 'fuente_identidad'),
                       'identidad_validada_en', 'identidad_validada_por'),
                      (('estado', 'fuente_estado'), 'estado_validado_en', 'estado_validado_por'))
            guardados = kwargs.get('update_fields')
            for campos, fecha, persona in grupos:
                relevantes = [c for c in campos if guardados is None or c in guardados]
                if (any(getattr(self, c) != getattr(anterior, c) for c in relevantes)
                        and getattr(self, fecha) == getattr(anterior, fecha)):
                    setattr(self, fecha, None)
                    setattr(self, persona, None)
                    invalidados.extend((fecha, persona))
        if kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = set(kwargs['update_fields']) | set(invalidados)
        return super().save(*args, **kwargs)

    def puede_gestionar(self, usuario):
        """Quien atiende sus solicitudes: su responsable, sus gestores y quien administra la plataforma."""
        if not getattr(usuario, 'is_authenticated', False):
            return False
        canonico = principal_vigente(usuario)
        if canonico is None:
            return False
        return (canonico.is_superuser or self.responsable_id == canonico.pk
                or self.gestores.filter(pk=canonico.pk).exists())


class GestorCentro(models.Model):
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, db_column='centroid_id', related_name='+')
    cuenta = models.ForeignKey(CuentaCentro, on_delete=models.PROTECT, db_column='user_id', related_name='+')

    class Meta:
        db_table = 'centros_id_centroid_gestores'
        unique_together = (('centro', 'cuenta'),)


class Componente(models.Model):
    """Un área del centro (capacidad propia): una división tecnológica, una plataforma de validación, un laboratorio
    de I+D o una instalación. Tiene su página: qué hace, cómo trabaja, sus equipos, lo que investiga y lo que presta.

    Si el área está registrada además como unidad operativa del directorio (un laboratorio de I+D), `unidad_slug`
    la enlaza y su ficha de unidad aporta la agenda, el inventario y el mantenimiento heredados.
    """
    TIPOS = [
        ('division', _('Área de tecnología aplicada')),
        ('plataforma', _('Plataforma operativa')),
        ('laboratorio', _('Laboratorio de I+D')),
        ('modulo', _('Módulo integrado')),
        ('transversal', _('Sistema transversal')),
        ('instalacion', _('Instalación de apoyo')),
    ]
    # Cómo se nombra un grupo de áreas del mismo tipo en la ficha («Divisiones tecnológicas», «Laboratorios de I+D»).
    TIPOS_PLURAL = {
        'division': _('Tecnologías aplicadas'), 'plataforma': _('Plataformas operativas'),
        'laboratorio': _('Laboratorios de I+D'), 'modulo': _('Módulos integrados'),
        'transversal': _('Sistemas transversales'), 'instalacion': _('Instalaciones de apoyo'),
    }
    ESTADOS = [
        ('operativa', _('Operativa')),
        ('implementacion', _('En implementación')),
        ('mantenimiento', _('En mantenimiento')),
    ]

    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='componentes', verbose_name=_('Centro'))
    integrado_en = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True,
        related_name='modulos', verbose_name=_('Integrado en el área'),
        help_text=_('Módulo de una plataforma del mismo centro. Conserva su ficha, recursos e historial.'))
    tipo = models.CharField(_('Tipo'), max_length=12, choices=TIPOS)
    codigo = models.SlugField(_('Código'), max_length=60)
    nombre = models.CharField(_('Nombre'), max_length=160)
    nombre_corto = models.CharField(_('Nombre corto'), max_length=60, blank=True)
    icono = models.CharField(_('Ícono'), max_length=40, default='fas fa-microchip',
                             help_text=_('Ícono de Font Awesome, por ejemplo «fas fa-robot».'))
    color = models.CharField(_('Color'), max_length=7, default='#1d5b3a')
    resumen = models.CharField(_('En una frase'), max_length=255)
    descripcion = models.TextField(_('Qué hace y por qué importa'))
    estado = models.CharField(_('Estado'), max_length=14, choices=ESTADOS, default='operativa')
    funciones = models.TextField(_('Funciones'), blank=True, help_text=_('Una por línea, «Función | descripción».'))
    capacidades = models.TextField(_('Capacidades'), blank=True, help_text=_('Una por línea, «Capacidad | uso».'))
    resultados = models.TextField(_('Resultados que entrega'), blank=True,
                                  help_text=_('Uno por línea, «Resultado | evidencia o aplicación».'))
    flujo = models.TextField(_('Cómo funciona, paso a paso'), blank=True,
                             help_text=_('Un paso por línea, «Paso | qué pasa». Los procesos detallados se registran aparte.'))
    equipamiento = models.TextField(_('Equipamiento'), blank=True,
                                    help_text=_('Una categoría por línea, «Categoría | equipos | función»; de aquí nacen '
                                                'los equipos del catálogo si no se registran uno a uno.'))
    software = models.TextField(_('Software y plataformas'), blank=True, help_text=_('Uno por línea, «Tipo | uso».'))
    organizacion_operativa = models.TextField(_('Sectores y operaciones'), blank=True,
        help_text=_('Una fila por línea: «Sector o celda | operación | control y evidencia».'))
    insumos_materiales = models.TextField(_('Insumos y materiales'), blank=True,
        help_text=_('Una fila por línea: «Material | especificación, uso y condiciones».'))
    usos_academicos = models.TextField(_('Actividades por carrera'), blank=True,
        help_text=_('Una fila por línea: «Carrera | actividad y forma de participación | evidencia que produce».'))
    seguridad = models.TextField(_('Riesgos y control'), blank=True,
                                 help_text=_('Una línea, «riesgos o necesidades | control requerido».'))
    unidades_articuladas = models.TextField(
        _('Unidades con las que se articula'), blank=True,
        help_text=_('El identificador público de cada laboratorio, planta o centro experimental, uno por línea.'))
    unidad_slug = models.SlugField(
        _('Unidad operativa propia'), max_length=160, blank=True,
        help_text=_('Si el área está registrada como unidad del directorio (laboratorio de I+D), su identificador.'))
    area_m2 = models.DecimalField(_('Área (m²)'), max_digits=7, decimal_places=1, null=True, blank=True)
    nivel = models.CharField(_('Nivel y código del área'), max_length=60, blank=True,
                             help_text=_('Por ejemplo «Nivel 1 · PB-02».'))
    videos = models.TextField(_('Videos'), blank=True,
                              help_text=_('Uno por línea, «ID de YouTube | título | canal | qué muestra».'))
    recorrido_360_url = models.URLField(_('Recorrido 360° del área'), blank=True)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)
    publicado = models.BooleanField(_('Publicado'), default=True)

    class Meta:
        verbose_name = _('Área del centro')
        verbose_name_plural = _('Áreas del centro')
        ordering = ('centro', 'orden', 'nombre')
        constraints = [models.UniqueConstraint(fields=('centro', 'codigo'), name='componente_codigo_por_centro'),
                       models.CheckConstraint(condition=~models.Q(pk=models.F('integrado_en')),
                                              name='cid_area_no_se_integra_en_si'),
                       models.UniqueConstraint(fields=('unidad_slug',), condition=~models.Q(unidad_slug=''),
                                               name='cid_laboratorio_propio_unico')]

    def __str__(self):
        return self.nombre_corto or self.nombre

    def clean(self):
        super().clean()
        if self.unidad_slug:
            if type(self).objects.filter(unidad_slug=self.unidad_slug).exclude(pk=self.pk).exists():
                raise ValidationError({'unidad_slug': _('Esta instalación ya figura como capacidad propia de otra área. '
                    'Para compartirla conserve su adscripción y registre una articulación.')})
            if self.unidad_slug in self.lista_unidades:
                raise ValidationError({'unidades_articuladas': _('La misma instalación no puede figurar '
                    'a la vez como propia y vinculada en esta área.')})
        if self.integrado_en_id:
            padre = self.integrado_en
            if padre.pk == self.pk or padre.centro_id != self.centro_id or padre.integrado_en_id:
                raise ValidationError({'integrado_en': _('Seleccione un área principal del mismo centro; no se admiten ciclos ni módulos anidados.')})
            if self.pk and self.modulos.exists():
                raise ValidationError({'integrado_en': _('Un área con módulos no puede convertirse en módulo de otra.')})

    es_division = property(lambda self: self.tipo == 'division')
    tipo_plural = property(lambda self: self.TIPOS_PLURAL.get(self.tipo, self.get_tipo_display()))
    lista_funciones = property(lambda self: pares_de(self.funciones))
    lista_capacidades = property(lambda self: pares_de(self.capacidades))
    lista_resultados = property(lambda self: pares_de(self.resultados))
    pasos = property(lambda self: pares_de(self.flujo))
    lista_equipamiento = property(lambda self: ternas_de(self.equipamiento))
    lista_software = property(lambda self: pares_de(self.software))
    sectores_operativos = property(lambda self: ternas_de(self.organizacion_operativa))
    lista_insumos = property(lambda self: pares_de(self.insumos_materiales))
    aplicaciones_academicas = property(lambda self: ternas_de(self.usos_academicos))
    control = property(lambda self: (pares_de(self.seguridad) or [('', '')])[0])
    lista_unidades = property(lambda self: lineas_de(self.unidades_articuladas))
    lista_videos = property(lambda self: _videos_de(self.videos))


class ImagenCentro(models.Model):
    """Una imagen del centro o de una de sus áreas, con su crédito: render, layout o foto."""
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='imagenes', verbose_name=_('Centro'))
    componente = models.ForeignKey(Componente, on_delete=models.CASCADE, null=True, blank=True,
                                   related_name='imagenes', verbose_name=_('Área'),
                                   help_text=_('Vacío: la imagen es del centro en general.'))
    imagen = models.ImageField(_('Imagen'), upload_to='centros_id/imagenes/')
    titulo = models.CharField(_('Qué muestra'), max_length=160)
    credito = models.CharField(_('Autor y licencia'), max_length=200, blank=True)
    fuente = models.URLField(_('Página de origen'), blank=True)
    es_plano = models.BooleanField(_('Es un plano o un diagrama'), default=False,
                                   help_text=_('Los planos y diagramas se muestran enteros, sin recorte.'))
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Imagen del centro')
        verbose_name_plural = _('Imágenes del centro')
        ordering = ('centro', 'componente', 'orden', 'pk')

    def __str__(self):
        return self.titulo


class PlanoCentro(models.Model):
    """El plano de un nivel del edificio; las áreas se ubican sobre él con sus coordenadas."""
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='planos', verbose_name=_('Centro'))
    nivel = models.CharField(_('Nivel'), max_length=60, help_text=_('El mismo nombre de nivel que usan las áreas.'))
    titulo = models.CharField(_('Qué muestra'), max_length=160)
    imagen = models.ImageField(_('Plano'), upload_to='centros_id/planos/')
    credito = models.CharField(_('Crédito'), max_length=200, blank=True)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Plano del edificio')
        verbose_name_plural = _('Planos del edificio')
        ordering = ('centro', 'orden')

    def __str__(self):
        return f'{self.nivel} · {self.titulo}'


class EquipoCentro(ContenidoCentro):
    """Un equipo o una categoría de equipamiento de un área, con su función y en qué procesos se usa."""
    ESTADOS = [
        ('operativo', _('Operativo')),
        ('planificado', _('Planificado o por adquirir')),
        ('mantenimiento', _('En mantenimiento')),
        ('baja', _('De baja')),
    ]

    componente = models.ForeignKey(Componente, on_delete=models.CASCADE, related_name='equipos', verbose_name=_('Área'))
    categoria = models.CharField(_('Categoría'), max_length=120)
    nombre = models.CharField(_('Equipo'), max_length=160)
    detalle = models.CharField(_('Qué incluye'), max_length=255, blank=True)
    funcion = models.CharField(_('Para qué sirve'), max_length=255, blank=True)
    especificaciones = models.TextField(_('Especificaciones'), blank=True, help_text=_('Una por línea, «dato | valor».'))
    cantidad = models.PositiveSmallIntegerField(_('Cantidad'), default=1)
    codigo = models.CharField(_('Código'), max_length=40, blank=True,
                              help_text=_('Etiqueta de bodega o código propio, para buscarlo y para su QR.'))
    estado = models.CharField(_('Estado'), max_length=14, choices=ESTADOS, default='operativo')
    es_activo_individual = models.BooleanField(_('Activo individual identificado'), default=False)
    reservable = models.BooleanField(_('Admite solicitudes de reserva'), default=False)
    requisitos = models.TextField(_('Requisitos de acceso'), blank=True)
    requiere_induccion = models.BooleanField(_('Requiere habilitación vigente'), default=False)
    requiere_supervision = models.BooleanField(_('Requiere supervisión'), default=True)
    calibracion_requerida = models.BooleanField(_('Requiere calibración vigente'), default=False)
    calibracion_hasta = models.DateField(_('Calibración válida hasta'), null=True, blank=True)
    calibracion_evidencia = models.CharField(_('Referencia de calibración'), max_length=500, blank=True)
    margen_minutos = models.PositiveSmallIntegerField(_('Preparación y cierre en minutos'), default=0)
    imagen = models.ImageField(_('Foto'), upload_to='centros_id/equipos/', blank=True)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Equipo del área')
        verbose_name_plural = _('Equipos de las áreas')
        ordering = ('componente', 'orden', 'categoria', 'nombre')

    def __str__(self):
        return self.nombre

    centro = property(lambda self: self.componente.centro)
    lista_especificaciones = property(lambda self: pares_de(self.especificaciones))

    @property
    def apto_reserva(self):
        from .escenarios import contenido_admitido
        return bool(contenido_admitido(self) and self.reservable and self.es_activo_individual and self.codigo.strip() and self.cantidad == 1
                    and self.estado == 'operativo' and self.componente.publicado
                    and self.componente.estado == 'operativa'
                    and (not self.calibracion_requerida or (self.calibracion_hasta
                         and self.calibracion_hasta >= timezone.localdate() and self.calibracion_evidencia.strip())))

    def clean(self):
        super().clean()
        if self.reservable and not (self.es_activo_individual and self.codigo.strip() and self.cantidad == 1):
            raise ValidationError(_('Una reserva requiere un activo individual con código y cantidad uno.'))


class ProcesoArea(models.Model):
    """Cómo trabaja un área: un proceso con sus pasos, subpasos, equipos, parámetros y controles."""
    componente = models.ForeignKey(Componente, on_delete=models.CASCADE, related_name='procesos', verbose_name=_('Área'))
    nombre = models.CharField(_('Proceso'), max_length=160)
    descripcion = models.TextField(_('Qué logra'), blank=True)
    entrada = models.CharField(_('Qué recibe'), max_length=200, blank=True)
    salida = models.CharField(_('Qué entrega'), max_length=200, blank=True)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)
    publicado = models.BooleanField(_('Publicado'), default=True)

    class Meta:
        verbose_name = _('Proceso del área')
        verbose_name_plural = _('Procesos de las áreas')
        ordering = ('componente', 'orden', 'nombre')

    def __str__(self):
        return self.nombre


class PasoProceso(models.Model):
    proceso = models.ForeignKey(ProcesoArea, on_delete=models.CASCADE, related_name='pasos', verbose_name=_('Proceso'))
    numero = models.PositiveSmallIntegerField(_('Paso'))
    nombre = models.CharField(_('Nombre'), max_length=160)
    descripcion = models.TextField(_('Qué pasa'), blank=True)
    subpasos = models.TextField(_('Subprocesos'), blank=True, help_text=_('Uno por línea, «Subpaso | detalle».'))
    parametros = models.CharField(_('Parámetros que se controlan'), max_length=255, blank=True)
    controles = models.CharField(_('Controles o registros'), max_length=255, blank=True)
    equipos = models.ManyToManyField(EquipoCentro, blank=True, related_name='pasos', verbose_name=_('Equipos que usa'))

    class Meta:
        verbose_name = _('Paso del proceso')
        verbose_name_plural = _('Pasos del proceso')
        ordering = ('proceso', 'numero')
        constraints = [models.UniqueConstraint(fields=('proceso', 'numero'), name='paso_numero_por_proceso')]

    def __str__(self):
        return f'{self.numero}. {self.nombre}'

    lista_subpasos = property(lambda self: pares_de(self.subpasos))


class RelacionArea(models.Model):
    """Qué entrega un área a otra: el mapa de relaciones del centro."""
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='relaciones_areas', verbose_name=_('Centro'))
    origen = models.ForeignKey(Componente, on_delete=models.CASCADE, related_name='entrega_a', verbose_name=_('Desde'))
    destino = models.ForeignKey(Componente, on_delete=models.CASCADE, related_name='recibe_de', verbose_name=_('Hacia'))
    que_fluye = models.CharField(_('Qué pasa de una a otra'), max_length=200)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Relación entre áreas')
        verbose_name_plural = _('Relaciones entre áreas')
        ordering = ('centro', 'orden')
        constraints = [models.UniqueConstraint(fields=('origen', 'destino'), name='relacion_area_unica')]

    def __str__(self):
        return f'{self.origen} → {self.destino}'

    def clean(self):
        if self.origen_id and self.destino_id and self.origen_id == self.destino_id:
            raise ValidationError({'destino': _('Un área no se relaciona consigo misma.')})
        if self.origen_id and self.destino_id and self.origen.centro_id != self.destino.centro_id:
            raise ValidationError({'destino': _('Las dos áreas deben ser del mismo centro.')})


class OrganoGobierno(models.Model):
    """Una instancia del modelo de gobierno: quién dirige, quién opera, quién evalúa, quién transfiere."""
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='gobierno', verbose_name=_('Centro'))
    nombre = models.CharField(_('Instancia'), max_length=160)
    rol = models.CharField(_('Rol principal'), max_length=120)
    responsabilidad = models.TextField(_('Responsabilidad general'))
    funciones = models.TextField(_('Funciones'), blank=True, help_text=_('Una por línea, «Función | descripción».'))
    icono = models.CharField(_('Ícono'), max_length=40, default='fas fa-sitemap')
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Instancia de gobierno')
        verbose_name_plural = _('Modelo de gobierno')
        ordering = ('centro', 'orden')

    def __str__(self):
        return self.nombre

    lista_funciones = property(lambda self: pares_de(self.funciones))


class EtapaOperativa(models.Model):
    """Una fase de la ruta con la que el centro convierte un reto en una solución transferida."""
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='ruta', verbose_name=_('Centro'))
    numero = models.PositiveSmallIntegerField(_('Número'))
    nombre = models.CharField(_('Etapa'), max_length=120)
    proposito = models.TextField(_('Propósito'))
    responsable = models.CharField(_('Responsable principal'), max_length=200, blank=True)
    resultado = models.CharField(_('Resultado esperado'), max_length=200)

    class Meta:
        verbose_name = _('Etapa de la ruta operativa')
        verbose_name_plural = _('Ruta operativa')
        ordering = ('centro', 'numero')
        constraints = [models.UniqueConstraint(fields=('centro', 'numero'), name='etapa_numero_por_centro')]

    def __str__(self):
        return f'{self.numero}. {self.nombre}'


class Modalidad(models.Model):
    """Una forma de usar el centro: investigación aplicada, docencia especializada, servicios externos…"""
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='modalidades', verbose_name=_('Centro'))
    nombre = models.CharField(_('Modalidad'), max_length=120)
    proposito = models.TextField(_('Propósito'))
    usuarios = models.CharField(_('Usuarios principales'), max_length=255)
    icono = models.CharField(_('Ícono'), max_length=40, default='fas fa-flask')
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Modalidad de funcionamiento')
        verbose_name_plural = _('Modalidades de funcionamiento')
        ordering = ('centro', 'orden')

    def __str__(self):
        return self.nombre


class LineaInvestigacion(models.Model):
    problema = models.TextField(_('Problema científico o tecnológico'), blank=True)
    objetivos = models.TextField(_('Objetivos de la línea'), blank=True)
    preguntas = models.TextField(_('Preguntas de investigación'), blank=True)
    metodologia = models.TextField(_('Métodos y enfoque'), blank=True)
    ambito = models.CharField(_('Ámbito o territorio'), max_length=200, blank=True)
    responsable = models.ForeignKey('Integrante', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='lineas_coordinadas', verbose_name=_('Responsable de la línea'))
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='lineas', verbose_name=_('Centro'))
    nombre = models.CharField(_('Línea de investigación'), max_length=160)
    resultados = models.TextField(_('Resultados que busca'))
    retos = models.TextField(_('Retos o problemas prioritarios'), blank=True, help_text=_('Uno por línea.'))
    retos_muestra = models.TextField(_('Ejemplos de retos pendientes de validación'), blank=True,
                                    help_text=_('Referencia interna; no se publica ni se suma a los retos institucionales.'))
    componente = models.ForeignKey(Componente, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='lineas', verbose_name=_('Área que la lidera'))
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Línea de investigación')
        verbose_name_plural = _('Líneas de investigación')
        ordering = ('centro', 'orden')

    def __str__(self):
        return self.nombre

    lista_retos = property(lambda self: lineas_de(self.retos))

    def clean(self):
        super().clean()
        for campo in ('responsable', 'componente'):
            relacionado = getattr(self, campo, None)
            if relacionado and self.centro_id and relacionado.centro_id != self.centro_id:
                raise ValidationError({campo: _('El registro debe pertenecer al mismo centro.')})


class Grupo(ContenidoCentro):
    """Un grupo de investigación que participa en el centro; conserva su identidad (art. 25)."""
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='grupos', verbose_name=_('Centro'))
    nombre = models.CharField(_('Grupo'), max_length=160)
    sigla = models.CharField(_('Sigla'), max_length=20, blank=True)
    descripcion = models.TextField(_('Qué investiga'), blank=True)
    facultad = models.CharField(_('Facultad o carrera'), max_length=160, blank=True)
    lineas = models.ManyToManyField(LineaInvestigacion, blank=True, related_name='grupos', verbose_name=_('Líneas'))
    enlace = models.URLField(_('Página del grupo'), blank=True)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)
    activo = models.BooleanField(_('Activo'), default=True)

    class Meta:
        verbose_name = _('Grupo de investigación')
        verbose_name_plural = _('Grupos de investigación')
        ordering = ('centro', 'orden', 'nombre')

    def __str__(self):
        return self.sigla or self.nombre


class Integrante(ContenidoCentro):
    """Una persona del centro: dirección, comité, investigadores, técnicos, tesistas y visitantes."""
    ROLES = [
        ('director', _('Dirección')),
        ('comite', _('Comité técnico-científico')),
        ('investigador', _('Investigador')),
        ('tecnico', _('Personal técnico')),
        ('asociado', _('Investigador asociado')),
        ('visitante', _('Investigador visitante')),
        ('tesista', _('Tesista')),
        ('estudiante', _('Estudiante o pasante')),
    ]
    PUBLICOS = ('director', 'comite', 'investigador', 'tecnico', 'asociado', 'visitante')

    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='integrantes', verbose_name=_('Centro'))
    nombre = models.CharField(_('Nombre'), max_length=160)
    rol = models.CharField(_('Rol'), max_length=14, choices=ROLES, default='investigador')
    cargo = models.CharField(_('Cargo o función'), max_length=160, blank=True,
                             help_text=_('Por ejemplo «Director del centro» o «Responsable técnico del FabLab».'))
    componente = models.ForeignKey(Componente, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='integrantes', verbose_name=_('Área'))
    grupo = models.ForeignKey(Grupo, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='integrantes', verbose_name=_('Grupo'))
    lineas = models.ManyToManyField(LineaInvestigacion, blank=True, related_name='integrantes', verbose_name=_('Líneas'))
    facultad = models.CharField(_('Facultad o institución de origen'), max_length=160, blank=True)
    perfil = models.TextField(_('Perfil'), blank=True)
    orcid = models.CharField('ORCID', max_length=40, blank=True)
    scholar = models.URLField(_('Google Scholar u otro perfil'), blank=True)
    foto = models.ImageField(_('Foto'), upload_to='centros_id/personas/', blank=True)
    vigente = models.BooleanField(_('Vigente'), default=True)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Integrante del centro')
        verbose_name_plural = _('Equipo del centro')
        ordering = ('centro', 'orden', 'nombre')

    def __str__(self):
        return self.nombre

    @property
    def enlace_orcid(self):
        return f'https://orcid.org/{self.orcid}' if self.orcid else ''

    @property
    def icono(self):
        return {'director': 'fas fa-user-tie', 'comite': 'fas fa-users-cog', 'investigador': 'fas fa-user-graduate',
                'tecnico': 'fas fa-tools', 'asociado': 'fas fa-user-plus', 'visitante': 'fas fa-globe',
                'tesista': 'fas fa-graduation-cap'}.get(self.rol, 'fas fa-user')

    @property
    def iniciales(self):
        return ''.join(parte[0] for parte in self.nombre.split()[:2]).upper()


class Servicio(models.Model):
    """Un servicio del portafolio: qué se hace, qué se entrega y quién lo pide."""
    USUARIOS = [('ambos', _('Usuarios internos y externos')), ('internos', _('Solo usuarios de la universidad')),
                ('externos', _('Usuarios externos'))]

    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='servicios', verbose_name=_('Centro'))
    linea = models.CharField(_('Línea de servicio'), max_length=120)
    componente = models.ForeignKey(Componente, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='servicios', verbose_name=_('Área que lo presta'))
    nombre = models.CharField(_('Servicio'), max_length=160)
    descripcion = models.CharField(_('Qué incluye'), max_length=255)
    entregable = models.CharField(_('Entregable'), max_length=160)
    usuarios = models.CharField(_('Para quién'), max_length=10, choices=USUARIOS, default='ambos')
    alcance = models.TextField(_('Alcance'), blank=True)
    exclusiones = models.TextField(_('Exclusiones'), blank=True)
    entradas = models.TextField(_('Qué debe aportar el solicitante'), blank=True)
    requisitos = models.TextField(_('Requisitos'), blank=True)
    metodo = models.TextField(_('Método o referencia técnica'), blank=True)
    formato_entrega = models.CharField(_('Formato de entrega'), max_length=160, blank=True)
    plazo = models.CharField(_('Plazo y condiciones de cómputo'), max_length=200, blank=True)
    aceptacion = models.TextField(_('Criterios de aceptación del entregable'), blank=True)
    condiciones = models.TextField(_('Condiciones de muestras, prototipos, software o confidencialidad'), blank=True)
    contacto = models.EmailField(_('Contacto autorizado'), blank=True)
    modalidad = models.CharField(_('Modalidad de atención'), max_length=16, default='tecnico',
                                  choices=[('tecnico', _('Servicio técnico')), ('diagnostico', _('Diagnóstico')),
                                           ('acompanamiento', _('Acompañamiento o asesoría'))])
    estado_oferta = models.CharField(_('Estado de oferta'), max_length=12, default='consultar',
                                     choices=[('consultar', _('Sujeto a evaluación')), ('disponible', _('Recibe solicitudes')),
                                              ('suspendido', _('Temporalmente suspendido'))])
    tarifa_fuente = models.CharField(_('Respaldo de tarifa'), max_length=500, blank=True)
    tarifa_fecha = models.DateField(_('Tarifa aprobada el'), null=True, blank=True)
    tarifa_hasta = models.DateField(_('Tarifa vigente hasta'), null=True, blank=True)
    tarifa = models.CharField(_('Tarifa aprobada'), max_length=120, blank=True,
                              help_text=_('Como la aprobó la Universidad; vacío mientras se cotiza caso por caso.'))
    activo = models.BooleanField(_('En el portafolio'), default=True)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Servicio tecnológico')
        verbose_name_plural = _('Portafolio de servicios')
        ordering = ('centro', 'orden', 'linea', 'nombre')

    def __str__(self):
        return self.nombre

    @property
    def tarifa_documentada(self):
        hoy = timezone.localdate()
        return bool(self.tarifa.strip() and self.tarifa_fuente.strip() and self.tarifa_fecha
                    and self.tarifa_fecha <= hoy and self.tarifa_hasta and hoy <= self.tarifa_hasta)

    @property
    def solicitable(self):
        return self.activo and self.estado_oferta != 'suspendido'

    def clean(self):
        super().clean()
        if self.componente_id and self.centro_id and self.componente.centro_id != self.centro_id:
            raise ValidationError({'componente': _('El área debe pertenecer al centro.')})
        if self.tarifa_fecha and self.tarifa_hasta and self.tarifa_hasta < self.tarifa_fecha:
            raise ValidationError({'tarifa_hasta': _('La vigencia termina antes de la aprobación.')})


class Zona(ContenidoCentro):
    """Un área del programa arquitectónico, con su nivel, sus dimensiones, el área del centro que aloja y su lugar
    en el plano."""
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='zonas', verbose_name=_('Centro'))
    codigo = models.CharField(_('Código'), max_length=20)
    nombre = models.CharField(_('Área'), max_length=160)
    nivel = models.CharField(_('Nivel'), max_length=60)
    dimensiones = models.CharField(_('Dimensiones'), max_length=60, blank=True)
    area_m2 = models.DecimalField(_('Superficie (m²)'), max_digits=7, decimal_places=1)
    componente = models.ForeignKey(Componente, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='zonas', verbose_name=_('Área del centro'))
    reservable = models.BooleanField(_('Se puede solicitar su acceso'), default=False,
                                     help_text=_('Las áreas con acceso solicitable aparecen al pedir acceso a una '
                                                 'capacidad del centro; el centro confirma el horario.'))
    estado_acceso = models.CharField(_('Estado de acceso'), max_length=14, default='no_habilitado',
                                     choices=[('no_habilitado', _('Pendiente de habilitación')),
                                              ('disponible', _('Habilitado')), ('bloqueado', _('Bloqueado'))])
    aforo = models.PositiveSmallIntegerField(_('Aforo autorizado'), null=True, blank=True)
    requisitos = models.TextField(_('Requisitos y actividades admitidas'), blank=True)
    accesibilidad = models.TextField(_('Condiciones de accesibilidad'), blank=True)
    margen_minutos = models.PositiveSmallIntegerField(_('Preparación y cierre en minutos'), default=0)
    plano_x = models.DecimalField(_('Posición en el plano (x %)'), max_digits=5, decimal_places=2, null=True, blank=True)
    plano_y = models.DecimalField(_('Posición en el plano (y %)'), max_digits=5, decimal_places=2, null=True, blank=True)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Espacio del edificio')
        verbose_name_plural = _('Espacios del edificio')
        ordering = ('centro', 'orden')

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    @property
    def en_plano(self):
        return self.plano_x is not None and self.plano_y is not None

    @property
    def apto_reserva(self):
        from .escenarios import contenido_admitido
        return bool(contenido_admitido(self) and self.reservable and self.estado_acceso == 'disponible' and self.aforo
                    and (not self.componente_id or (self.componente.publicado and self.componente.estado == 'operativa')))


class Fase(models.Model):
    ESTADOS = [('pendiente', _('Pendiente')), ('en_curso', _('En curso')), ('cumplida', _('Cumplida'))]

    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='fases', verbose_name=_('Centro'))
    numero = models.PositiveSmallIntegerField(_('Fase'))
    nombre = models.CharField(_('Denominación'), max_length=160)
    actividades = models.TextField(_('Actividades principales'))
    horizonte = models.CharField(_('Horizonte'), max_length=60)
    estado = models.CharField(_('Estado'), max_length=10, choices=ESTADOS, default='pendiente')

    class Meta:
        verbose_name = _('Fase de implementación')
        verbose_name_plural = _('Fases de implementación')
        ordering = ('centro', 'numero')
        constraints = [models.UniqueConstraint(fields=('centro', 'numero'), name='fase_numero_por_centro')]

    def __str__(self):
        return f'Fase {self.numero}: {self.nombre}'


class PartidaPresupuesto(models.Model):
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='presupuesto', verbose_name=_('Centro'))
    concepto = models.CharField(_('Concepto'), max_length=160)
    contenido = models.CharField(_('Qué incluye'), max_length=255, blank=True)
    monto = models.DecimalField(_('Monto (USD)'), max_digits=12, decimal_places=2, null=True, blank=True,
                                help_text=_('Vacío cuando todavía se define en una etapa posterior.'))
    nota = models.CharField(_('Nota'), max_length=200, blank=True)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Partida del presupuesto')
        verbose_name_plural = _('Presupuesto referencial')
        ordering = ('centro', 'orden')

    def __str__(self):
        return self.concepto


class Indicador(models.Model):
    """Lo que el centro mide para saber si se usa y si transfiere. Con un cálculo, el valor sale solo de los registros
    del centro; sin él, el centro registra cada medición con su fecha."""
    CALCULOS = [
        ('', _('Se registra a mano')),
        ('proyectos_activos', _('Proyectos en formulación o en ejecución')),
        ('proyectos_concluidos', _('Proyectos finalizados o transferidos')),
        ('proyectos_con_aliados', _('Proyectos con aliados externos')),
        ('investigadores', _('Investigadores y asociados vigentes')),
        ('en_formacion', _('Tesistas y estudiantes vigentes')),
        ('produccion', _('Producción científica publicada')),
        ('datos_y_software', _('Conjuntos de datos y software publicados')),
        ('propiedad_intelectual', _('Registros de propiedad intelectual')),
        ('prototipos', _('Prototipos y desarrollos')),
        ('casos', _('Casos de éxito documentados')),
        ('aliados', _('Aliados vigentes')),
        ('servicios', _('Servicios en el portafolio')),
    ]
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='indicadores', verbose_name=_('Centro'))
    categoria = models.CharField(_('Categoría'), max_length=80)
    nombre = models.CharField(_('Indicador'), max_length=160)
    medicion = models.CharField(_('Cómo se mide'), max_length=255)
    calculo = models.CharField(_('Cálculo automático'), max_length=24, choices=CALCULOS, blank=True,
                               help_text=_('Con un cálculo, el valor se cuenta solo desde los registros del centro.'))
    meta = models.CharField(_('Meta'), max_length=80, blank=True)
    valor = models.DecimalField(_('Valor actual'), max_digits=12, decimal_places=2, null=True, blank=True)
    actualizado = models.DateField(_('Fecha del valor'), null=True, blank=True)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Indicador')
        verbose_name_plural = _('Indicadores de resultado e impacto')
        ordering = ('centro', 'orden')

    def __str__(self):
        return self.nombre


class Riesgo(models.Model):
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='riesgos', verbose_name=_('Centro'))
    categoria = models.CharField(_('Tipo de riesgo'), max_length=80)
    riesgo = models.CharField(_('Riesgo'), max_length=160)
    efecto = models.CharField(_('Posible efecto'), max_length=200)
    mitigacion = models.CharField(_('Medida de mitigación'), max_length=255)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Riesgo y mitigación')
        verbose_name_plural = _('Riesgos y mitigación')
        ordering = ('centro', 'orden')

    def __str__(self):
        return self.riesgo


class Articulacion(models.Model):
    """Con quién se articula el centro y para qué: una unidad de la universidad (capacidad vinculada), una carrera o
    un tipo de actor externo. El instrumento de vinculación de una unidad se guarda aquí (art. 26)."""
    TIPOS = [('unidad', _('Unidad de la universidad')), ('carrera', _('Carrera o área académica')),
             ('futura', _('Carrera o programa futuro')), ('externo', _('Actor externo'))]

    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='articulaciones', verbose_name=_('Centro'))
    tipo = models.CharField(_('Tipo'), max_length=10, choices=TIPOS)
    actor = models.CharField(_('Con quién'), max_length=160)
    forma = models.CharField(_('Para qué'), max_length=255)
    unidad_slug = models.SlugField(_('Identificador de la unidad'), max_length=160, blank=True,
                                   help_text=_('Si es una unidad del directorio, su identificador público: enlaza a su ficha.'))
    instrumento = models.CharField(_('Instrumento de vinculación'), max_length=200, blank=True,
                                   help_text=_('Resolución, convenio o acuerdo que formaliza la vinculación.'))
    vigencia_hasta = models.DateField(_('Vigente hasta'), null=True, blank=True)
    MODALIDADES = [
        ('capacidad', _('Acceso a la capacidad para proyectos del centro')),
        ('servicio', _('Prestación de servicios')),
        ('proyecto', _('Proyectos conjuntos')),
        ('docencia', _('Docencia y formación')),
        ('datos', _('Datos y análisis')),
    ]
    modalidad = models.CharField(_('Modalidad de acceso'), max_length=10, choices=MODALIDADES, blank=True,
                                 help_text=_('Cómo usa el centro esta capacidad; la fija el instrumento de vinculación.'))
    reglas = models.CharField(_('Reglas de uso'), max_length=255, blank=True,
                              help_text=_('Prioridades, horarios, costos o condiciones acordadas con la unidad.'))
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Articulación')
        verbose_name_plural = _('Articulación institucional y externa')
        ordering = ('centro', 'tipo', 'orden')

    def __str__(self):
        return f'{self.actor} · {self.get_tipo_display()}'


class Aliado(ContenidoCentro):
    """Una institución aliada, un convenio, una red o un emprendimiento nacido del centro."""
    ROL_COLABORACION = [('colaborador', _('Colaborador')), ('financiador', _('Financiador')),
                       ('proveedor', _('Proveedor')), ('beneficiario', _('Beneficiario'))]
    rol_colaboracion = models.CharField(_('Relación con el centro'), max_length=14, choices=ROL_COLABORACION,
                                        default='colaborador')
    vigencia_desde = models.DateField(_('Inicio de vigencia'), null=True, blank=True)
    actividades = models.TextField(_('Actividades concretas de colaboración'), blank=True)
    responsable = models.ForeignKey(Integrante, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='alianzas_a_cargo', verbose_name=_('Responsable de la relación'))
    TIPOS = [
        ('empresa', _('Empresa')), ('gad', _('Gobierno local')), ('institucion', _('Institución pública')),
        ('universidad', _('Universidad o centro de investigación')), ('organismo', _('Organismo de cooperación')),
        ('red', _('Red o consorcio')), ('asociacion', _('Asociación o comunidad')),
        ('emprendimiento', _('Emprendimiento o spin-off')),
    ]

    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='aliados', verbose_name=_('Centro'))
    nombre = models.CharField(_('Nombre'), max_length=160)
    tipo = models.CharField(_('Tipo'), max_length=16, choices=TIPOS)
    pais = models.CharField(_('País'), max_length=60, blank=True)
    aporte = models.CharField(_('Qué aporta o qué se hace juntos'), max_length=255, blank=True)
    convenio = models.CharField(_('Convenio o instrumento'), max_length=200, blank=True)
    vigencia_hasta = models.DateField(_('Vigente hasta'), null=True, blank=True)
    enlace = models.URLField(_('Sitio web'), blank=True)
    logo = models.ImageField(_('Logotipo'), upload_to='centros_id/aliados/', blank=True)
    activo = models.BooleanField(_('Mostrar en el catálogo'), default=True)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Aliado o convenio')
        verbose_name_plural = _('Alianzas y convenios')
        ordering = ('centro', 'orden', 'nombre')

    def __str__(self):
        return self.nombre

    @property
    def icono(self):
        return {'empresa': 'fas fa-industry', 'gad': 'fas fa-landmark', 'institucion': 'fas fa-university',
                'universidad': 'fas fa-graduation-cap', 'organismo': 'fas fa-globe-americas', 'red': 'fas fa-network-wired',
                'asociacion': 'fas fa-people-carry', 'emprendimiento': 'fas fa-seedling'}.get(self.tipo, 'fas fa-handshake')
    @property
    def vigente(self):
        from .escenarios import contenido_admitido
        hoy = timezone.localdate()
        return bool(self.activo and contenido_admitido(self) and self.convenio.strip() and self.fuente_validacion.strip()
                    and self.vigencia_desde and self.vigencia_hasta and self.vigencia_desde <= hoy <= self.vigencia_hasta)

    @property
    def estado_vinculo(self):
        if self.vigente:
            return _('Vigencia documentada')
        if self.vigencia_hasta and self.vigencia_hasta < timezone.localdate():
            return _('Instrumento vencido')
        if self.vigencia_desde and self.vigencia_desde > timezone.localdate():
            return _('Inicio futuro')
        return _('Vigencia pendiente de respaldo')

    def clean(self):
        super().clean()
        if self.vigencia_desde and self.vigencia_hasta and self.vigencia_hasta < self.vigencia_desde:
            raise ValidationError({'vigencia_hasta': _('La vigencia termina antes de empezar.')})
        if self.responsable_id and self.centro_id and self.responsable.centro_id != self.centro_id:
            raise ValidationError({'responsable': _('El responsable debe pertenecer al mismo centro.')})


class Proyecto(ContenidoCentro):
    ESTADOS = [('formulacion', _('En formulación')), ('ejecucion', _('En ejecución')),
               ('finalizado', _('Finalizado')), ('transferido', _('Transferido')),
               ('suspendido', _('Suspendido')), ('cancelado', _('Cancelado'))]
    ETAPAS = [
        ('problema', _('Identificación del problema')), ('desarrollo', _('Experimentación o desarrollo')),
        ('prototipado', _('Prototipado')), ('validacion', _('Validación')), ('documentacion', _('Documentación')),
        ('proteccion', _('Protección de resultados')), ('transferencia', _('Transferencia o adopción')),
    ]
    CATEGORIAS = [('investigacion', _('Investigación aplicada')), ('desarrollo', _('Desarrollo experimental')),
                  ('innovacion', _('Innovación')), ('otro', _('Otra actividad'))]
    categoria = models.CharField(_('Categoría de actividad'), max_length=16, choices=CATEGORIAS, default='investigacion')
    sector = models.CharField(_('Sector'), max_length=100, blank=True)
    problema = models.TextField(_('Problema que aborda'), blank=True)
    objetivos = models.TextField(_('Objetivos del proyecto'), blank=True)
    metodologia = models.TextField(_('Metodología resumida'), blank=True)
    avance_metodo = models.CharField(_('Método de cálculo del avance'), max_length=255, blank=True)
    avance_fecha = models.DateField(_('Fecha de corte del avance'), null=True, blank=True)
    avance_evidencia = models.CharField(_('Evidencia del avance'), max_length=500, blank=True)
    monto_publico = models.BooleanField(_('Autoriza publicar el monto'), default=False)
    ACTIVOS = ('formulacion', 'ejecucion')

    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='proyectos', verbose_name=_('Centro'))
    codigo = models.CharField(_('Código'), max_length=40, blank=True)
    titulo = models.CharField(_('Título'), max_length=200)
    resumen = models.TextField(_('Resumen'))
    linea = models.ForeignKey(LineaInvestigacion, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='proyectos', verbose_name=_('Línea de investigación'))
    componentes = models.ManyToManyField(Componente, blank=True, related_name='proyectos',
                                         verbose_name=_('Áreas que intervienen'))
    estado = models.CharField(_('Estado'), max_length=12, choices=ESTADOS, default='formulacion')
    etapa = models.CharField(_('Etapa de la ruta'), max_length=14, choices=ETAPAS, default='problema',
                             help_text=_('Actividad actual; no acredita completar otras etapas ni obliga a patentar.'))
    avance = models.PositiveSmallIntegerField(_('Avance (%)'), null=True, blank=True,
                                              validators=[MaxValueValidator(100)])
    financiador = models.CharField(_('Entidad financiadora'), max_length=160, blank=True)
    monto = models.DecimalField(_('Monto financiado (USD)'), max_digits=12, decimal_places=2, null=True, blank=True)
    responsable = models.ForeignKey(Integrante, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='proyectos_dirigidos', verbose_name=_('Investigador responsable'))
    equipo = models.ManyToManyField(Integrante, blank=True, related_name='proyectos', verbose_name=_('Equipo'))
    aliados = models.ManyToManyField(Aliado, blank=True, related_name='proyectos', verbose_name=_('Aliados'))
    investigadores = models.PositiveSmallIntegerField(_('Investigadores'), null=True, blank=True,
                                                      help_text=_('Si no se registran uno a uno.'))
    inicio = models.DateField(_('Inicio'), null=True, blank=True)
    fin = models.DateField(_('Fin'), null=True, blank=True)
    hitos = models.TextField(_('Hitos'), blank=True, help_text=_('Uno por línea, «fecha o periodo | hito».'))
    enlace = models.URLField(_('Enlace'), blank=True)
    imagen = models.ImageField(_('Imagen'), upload_to='centros_id/proyectos/', blank=True)
    destacado = models.BooleanField(_('Destacado en la portada'), default=False)
    publicado = models.BooleanField(_('Publicado'), default=True)

    class Meta:
        verbose_name = _('Proyecto I+D+i')
        verbose_name_plural = _('Proyectos I+D+i')
        ordering = ('centro', '-destacado', '-inicio', 'titulo')

    def __str__(self):
        return self.titulo

    lista_hitos = property(lambda self: pares_de(self.hitos))

    @property
    def activo(self):
        return self.estado in self.ACTIVOS

    @property
    def transferencia_documentada(self):
        from .escenarios import contenido_admitido
        return any(c.centro_id == self.centro_id and c.publicado and contenido_admitido(c)
                   and c.transferencia_documentada for c in self.casos.all())

    @property
    def estado_publico(self):
        if self.estado == 'transferido' and not self.transferencia_documentada:
            return _('Transferencia pendiente de documentar')
        return self.get_estado_display()

    @property
    def avance_acreditado(self):
        return (self.avance is not None and bool(self.avance_metodo.strip() and self.avance_fecha
                                                and self.avance_evidencia.strip() and self.avance_fecha <= timezone.localdate()))

    @property
    def etapas_recorridas(self):
        # Una etapa seleccionada no demuestra que el proyecto haya pasado por todas las anteriores.
        return [self.etapa] if self.etapa in dict(self.ETAPAS) else []

    def clean(self):
        super().clean()
        if self.inicio and self.fin and self.fin < self.inicio:
            raise ValidationError({'fin': _('La fecha final no puede preceder al inicio.')})
        for campo in ('linea', 'responsable'):
            relacionado = getattr(self, campo, None)
            if relacionado and self.centro_id and relacionado.centro_id != self.centro_id:
                raise ValidationError({campo: _('El registro debe pertenecer al mismo centro.')})


class HitoProyecto(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='hitos_registrados')
    titulo = models.CharField(_('Hito'), max_length=200)
    fecha_prevista = models.DateField(_('Fecha prevista'))
    estado = models.CharField(_('Estado'), max_length=12, default='pendiente',
                              choices=[('pendiente', _('Pendiente')), ('cumplido', _('Cumplido')),
                                       ('cancelado', _('Cancelado'))])
    fecha_cumplida = models.DateField(_('Fecha de cumplimiento'), null=True, blank=True)
    evidencia = models.CharField(_('Evidencia de cumplimiento'), max_length=500, blank=True)
    publico = models.BooleanField(_('Publicar el hito'), default=False)

    class Meta:
        ordering = ('fecha_prevista', 'pk')
        verbose_name = _('Hito del proyecto')
        verbose_name_plural = _('Hitos del proyecto')

    def __str__(self):
        return self.titulo

    @property
    def vencido(self):
        return self.estado == 'pendiente' and self.fecha_prevista < timezone.localdate()

    @property
    def cumplimiento_documentado(self):
        return bool(self.estado == 'cumplido' and self.fecha_cumplida and self.evidencia.strip()
                    and self.fecha_cumplida <= timezone.localdate())

    @property
    def estado_publico(self):
        if self.estado == 'cumplido' and not self.cumplimiento_documentado:
            return _('Cumplimiento pendiente de documentar')
        return self.get_estado_display()

    def clean(self):
        super().clean()
        if self.estado == 'cumplido' and not self.cumplimiento_documentado:
            raise ValidationError(_('Un hito cumplido requiere fecha y evidencia.'))


class Resultado(ContenidoCentro):
    """Lo que el centro produce: publicaciones, datos, software, métodos, tesis, prototipos, propiedad intelectual e
    informes. Cada resultado se asocia a su proyecto, a sus autores y al área que lo generó (art. 29)."""
    TIPOS = [
        ('publicacion', _('Publicación')), ('dato', _('Conjunto de datos')), ('software', _('Software')),
        ('metodo', _('Método o protocolo')), ('tesis', _('Tesis o trabajo de titulación')),
        ('prototipo', _('Prototipo o desarrollo')), ('propiedad_intelectual', _('Propiedad intelectual')),
        ('informe', _('Informe técnico')), ('otro', _('Otro resultado')),
    ]
    CIENTIFICOS = ('publicacion', 'dato', 'software', 'metodo', 'tesis', 'informe')
    INNOVACION = ('prototipo', 'propiedad_intelectual')
    ACCESOS = [('abierto', _('Acceso abierto')), ('embargo', _('Bajo embargo')), ('restringido', _('Acceso restringido'))]
    acceso = models.CharField(_('Condición de acceso'), max_length=12, choices=ACCESOS, default='abierto')
    embargo_hasta = models.DateField(_('Embargo hasta'), null=True, blank=True)
    version = models.CharField(_('Versión del resultado'), max_length=80, blank=True)
    doi = models.CharField('DOI', max_length=255, blank=True)
    sector = models.CharField(_('Sector de aplicación'), max_length=100, blank=True)
    tecnologia = models.CharField(_('Tecnología'), max_length=160, blank=True)
    usuarios_previstos = models.TextField(_('Usuarios y necesidad que atiende'), blank=True)
    colaboracion = models.TextField(_('Modalidades y condiciones de colaboración'), blank=True)
    trl_fecha = models.DateField(_('Fecha de valoración TRL'), null=True, blank=True)
    trl_evaluador = models.CharField(_('Evaluador TRL'), max_length=200, blank=True)
    trl_alcance = models.TextField(_('Alcance de la valoración TRL'), blank=True)
    trl_evidencia = models.CharField(_('Respaldo de la valoración TRL'), max_length=500, blank=True)
    pi_modalidad = models.CharField(_('Modalidad de protección'), max_length=120, blank=True)
    pi_titular = models.CharField(_('Titular de los derechos'), max_length=200, blank=True)
    pi_identificador = models.CharField(_('Identificador divulgable de protección'), max_length=160, blank=True)
    pi_fecha = models.DateField(_('Fecha del estado de protección'), null=True, blank=True)
    pi_evidencia = models.CharField(_('Respaldo del estado de protección'), max_length=500, blank=True)
    restricciones = models.TextField(_('Restricciones y condiciones de divulgación'), blank=True)
    CUARTILES = [('', _('Sin cuartil')), ('Q1', 'Q1'), ('Q2', 'Q2'), ('Q3', 'Q3'), ('Q4', 'Q4')]
    ESTADOS_PI = [('', '—'), ('solicitada', _('Solicitada')), ('concedida', _('Concedida')), ('registrada', _('Registrada'))]

    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='resultados', verbose_name=_('Centro'))
    tipo = models.CharField(_('Tipo'), max_length=22, choices=TIPOS, default='publicacion')
    titulo = models.CharField(_('Título'), max_length=255)
    descripcion = models.TextField(_('Descripción'), blank=True)
    revista = models.CharField(_('Revista, evento, repositorio o registro'), max_length=200, blank=True)
    anio = models.PositiveSmallIntegerField(_('Año'))
    cuartil = models.CharField(_('Cuartil'), max_length=2, choices=CUARTILES, blank=True)
    enlace = models.URLField(_('DOI o enlace'), blank=True)
    archivo = models.FileField(_('Archivo'), upload_to='centros_id/resultados/', blank=True)
    proyecto = models.ForeignKey(Proyecto, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='resultados', verbose_name=_('Proyecto'))
    componente = models.ForeignKey(Componente, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='resultados_generados', verbose_name=_('Área que lo generó'))
    autores = models.ManyToManyField(Integrante, blank=True, related_name='resultados', verbose_name=_('Autores del centro'))
    autores_texto = models.CharField(_('Autores'), max_length=255, blank=True,
                                     help_text=_('Como se citan, incluidos los externos.'))
    trl = models.PositiveSmallIntegerField(_('Nivel de madurez (TRL)'), null=True, blank=True,
                                           validators=[MinValueValidator(1), MaxValueValidator(9)])
    estado_pi = models.CharField(_('Estado de la protección'), max_length=12, choices=ESTADOS_PI, blank=True)
    licencia = models.CharField(_('Licencia'), max_length=80, blank=True)
    confidencial = models.BooleanField(_('Confidencial'), default=False,
                                       help_text=_('No se publica mientras se protege o negocia (art. 29).'))
    publicado = models.BooleanField(_('Publicado'), default=True)

    class Meta:
        verbose_name = _('Resultado')
        verbose_name_plural = _('Producción y resultados')
        ordering = ('centro', '-anio', 'titulo')
        constraints = [models.UniqueConstraint(fields=('centro', 'doi'), condition=~models.Q(doi=''),
                                                name='cid_resultado_doi_unico')]

    def __str__(self):
        return self.titulo

    @property
    def visible(self):
        from .escenarios import contenido_admitido
        return self.publicado and not self.confidencial and contenido_admitido(self)

    @property
    def icono(self):
        return {'publicacion': 'fas fa-book-open', 'dato': 'fas fa-database', 'software': 'fas fa-code',
                'metodo': 'fas fa-vial', 'tesis': 'fas fa-graduation-cap', 'prototipo': 'fas fa-cogs',
                'propiedad_intelectual': 'fas fa-certificate', 'informe': 'fas fa-file-alt'}.get(self.tipo, 'fas fa-star')

    @property
    def acceso_abierto(self):
        return self.acceso == 'abierto' or (self.acceso == 'embargo' and self.embargo_hasta
                                           and self.embargo_hasta < timezone.localdate())

    @property
    def estado_acceso_publico(self):
        if self.acceso == 'embargo' and self.acceso_abierto:
            return _('Embargo finalizado')
        return self.get_acceso_display()

    @property
    def trl_documentado(self):
        return bool(self.trl and self.trl_fecha and self.trl_evaluador.strip()
                    and self.trl_alcance.strip() and self.trl_evidencia.strip() and self.trl_fecha <= timezone.localdate())

    @property
    def pi_documentada(self):
        return bool(self.estado_pi and self.pi_modalidad.strip() and self.pi_titular.strip()
                    and self.pi_fecha and self.pi_fecha <= timezone.localdate() and self.pi_evidencia.strip())

    @property
    def url_doi(self):
        return 'https://doi.org/' + quote(self.doi, safe='/') if self.doi else ''

    @property
    def url(self):
        if self.confidencial or not self.acceso_abierto:
            return ''
        return self.archivo.url if self.archivo else self.enlace

    def clean(self):
        super().clean()
        self.doi = normalizar_doi(self.doi)
        if self.doi and (not re.fullmatch(r'10[.][0-9]+(?:[.][0-9]+)*/.+', self.doi)
                         or any(unicodedata.category(c)[0] not in 'LMNPS' and unicodedata.category(c) != 'Zs'
                                for c in self.doi)):
            raise ValidationError({'doi': _('Registre un DOI completo con prefijo y sufijo, o déjelo vacío.')})
        if self.acceso == 'embargo' and not self.embargo_hasta:
            raise ValidationError({'embargo_hasta': _('Indique hasta cuándo se mantiene el embargo.')})
        if (self.confidencial or not self.acceso_abierto) and self.archivo:
            raise ValidationError({'archivo': _('Este almacenamiento es público. Registre solo metadatos para resultados restringidos o bajo embargo; conserve el archivo en un repositorio con control de acceso.')})
        for campo in ('proyecto', 'componente'):
            relacionado = getattr(self, campo, None)
            if relacionado and self.centro_id and relacionado.centro_id != self.centro_id:
                raise ValidationError({campo: _('El registro debe pertenecer al mismo centro.')})

    def save(self, *args, **kwargs):
        if self.archivo and (self.confidencial or not self.acceso_abierto):
            raise ValidationError({'archivo': _('Los archivos confidenciales, restringidos o bajo embargo deben conservarse en un repositorio con control de acceso.')})
        self.doi = normalizar_doi(self.doi)
        if self.doi and kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = set(kwargs['update_fields']) | {'doi'}
        return super().save(*args, **kwargs)


class CasoExito(ContenidoCentro):
    """Un resultado que cambió algo fuera del centro: quién se benefició, qué reto tenía y qué se logró."""
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='casos', verbose_name=_('Centro'))
    contexto = models.TextField(_('Contexto y período observado'), blank=True)
    aporte_centro = models.TextField(_('Papel del centro'), blank=True)
    receptor = models.CharField(_('Receptor de la transferencia'), max_length=200, blank=True)
    mecanismo = models.CharField(_('Mecanismo de transferencia o adopción'), max_length=200, blank=True)
    fecha_transferencia = models.DateField(_('Fecha de aceptación o adopción'), null=True, blank=True)
    evidencia = models.CharField(_('Evidencia de aceptación o uso'), max_length=500, blank=True)
    referencia = models.TextField(_('Situación de referencia'), blank=True)
    unidad_medida = models.CharField(_('Unidad de medida'), max_length=80, blank=True)
    periodo_medicion = models.CharField(_('Período de medición'), max_length=120, blank=True)
    metodo_medicion = models.TextField(_('Método de medición'), blank=True)
    limites = models.TextField(_('Límites de atribución'), blank=True)
    autorizacion_publicacion = models.CharField(_('Respaldo de autorización para divulgar el caso'), max_length=500, blank=True)
    desarrollo = models.ForeignKey(Resultado, on_delete=models.SET_NULL, null=True, blank=True, related_name='casos')
    titulo = models.CharField(_('Título'), max_length=200)
    beneficiario = models.CharField(_('Beneficiario'), max_length=160)
    sector = models.CharField(_('Sector'), max_length=80, blank=True)
    reto = models.TextField(_('El reto'))
    solucion = models.TextField(_('Lo que se hizo'))
    resultado = models.CharField(_('Resultado medible'), max_length=255)
    componente = models.ForeignKey(Componente, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='casos', verbose_name=_('Área que lo hizo posible'))
    proyecto = models.ForeignKey(Proyecto, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='casos', verbose_name=_('Proyecto'))
    aliado = models.ForeignKey(Aliado, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='casos', verbose_name=_('Aliado'))
    anio = models.PositiveSmallIntegerField(_('Año'))
    imagen = models.ImageField(_('Imagen'), upload_to='centros_id/casos/', blank=True)
    enlace = models.URLField(_('Enlace'), blank=True)
    publicado = models.BooleanField(_('Publicado'), default=True)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Caso de éxito')
        verbose_name_plural = _('Casos de éxito y transferencia')
        ordering = ('centro', 'orden', '-anio')

    def __str__(self):
        return self.titulo


    @property
    def transferencia_documentada(self):
        return bool(self.receptor.strip() and self.mecanismo.strip() and self.fecha_transferencia
                    and self.fecha_transferencia <= timezone.localdate()
                    and self.evidencia.strip() and self.autorizacion_publicacion.strip())

    @property
    def impacto_documentado(self):
        return self.transferencia_documentada and bool(self.referencia.strip() and self.unidad_medida.strip()
                                                       and self.periodo_medicion.strip() and self.metodo_medicion.strip())

    def clean(self):
        super().clean()
        for campo in ('proyecto', 'desarrollo', 'aliado', 'componente'):
            relacionado = getattr(self, campo, None)
            if relacionado and self.centro_id and relacionado.centro_id != self.centro_id:
                raise ValidationError({campo: _('El registro debe pertenecer al mismo centro.')})
        if self.desarrollo_id and self.proyecto_id and self.desarrollo.proyecto_id not in (None, self.proyecto_id):
            raise ValidationError({'desarrollo': _('El desarrollo corresponde a otro proyecto.')})


class Convocatoria(ContenidoCentro):
    """Una puerta para sumarse al centro: temas de tesis, pasantías, plazas de investigación, convocatorias."""
    TIPOS = [('tesis', _('Tema de tesis')), ('pasantia', _('Pasantía o práctica')), ('investigador', _('Plaza o estancia')),
             ('convocatoria', _('Convocatoria o fondo')), ('empleo', _('Vacante')), ('otro', _('Otra oportunidad'))]

    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='convocatorias', verbose_name=_('Centro'))
    tipo = models.CharField(_('Tipo'), max_length=14, choices=TIPOS)
    titulo = models.CharField(_('Título'), max_length=200)
    descripcion = models.TextField(_('De qué se trata y qué se pide'))
    componente = models.ForeignKey(Componente, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='convocatorias', verbose_name=_('Área'))
    cierre = models.DateField(_('Cierra'), null=True, blank=True)
    enlace = models.URLField(_('Enlace o formulario'), blank=True)
    activa = models.BooleanField(_('Abierta'), default=True)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Convocatoria u oportunidad')
        verbose_name_plural = _('Convocatorias y oportunidades')
        ordering = ('centro', 'orden', 'cierre')

    def __str__(self):
        return self.titulo

    @property
    def vigente(self):
        return self.activa and (self.cierre is None or self.cierre >= timezone.localdate())

    @property
    def icono(self):
        return {'tesis': 'fas fa-graduation-cap', 'pasantia': 'fas fa-user-clock', 'investigador': 'fas fa-user-graduate',
                'convocatoria': 'fas fa-bullhorn', 'empleo': 'fas fa-briefcase'}.get(self.tipo, 'fas fa-door-open')


class Novedad(ContenidoCentro):
    """Una noticia, un evento, un reconocimiento o una aparición en prensa del centro."""
    TIPOS = [('noticia', _('Noticia')), ('evento', _('Evento')), ('reconocimiento', _('Reconocimiento o premio')),
             ('prensa', _('En la prensa'))]

    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='novedades', verbose_name=_('Centro'))
    tipo = models.CharField(_('Tipo'), max_length=16, choices=TIPOS, default='noticia')
    titulo = models.CharField(_('Título'), max_length=200)
    resumen = models.TextField(_('Resumen'))
    fecha = models.DateField(_('Fecha'))
    fecha_fin = models.DateField(_('Termina'), null=True, blank=True, help_text=_('Para eventos de varios días.'))
    lugar = models.CharField(_('Lugar'), max_length=160, blank=True)
    enlace = models.URLField(_('Enlace'), blank=True)
    imagen = models.ImageField(_('Imagen'), upload_to='centros_id/novedades/', blank=True)
    publicada = models.BooleanField(_('Publicada'), default=True)

    class Meta:
        verbose_name = _('Novedad')
        verbose_name_plural = _('Noticias y eventos')
        ordering = ('centro', '-fecha')

    def __str__(self):
        return self.titulo

    @property
    def proximo(self):
        return self.tipo == 'evento' and (self.fecha_fin or self.fecha) >= timezone.localdate()

    @property
    def icono(self):
        return {'evento': 'fas fa-calendar-alt', 'reconocimiento': 'fas fa-award',
                'prensa': 'fas fa-newspaper'}.get(self.tipo, 'fas fa-bullhorn')


class DocumentoCentro(ContenidoCentro):
    """Los documentos de gobierno y normativa del centro: plan, informes, actas, reglamento, políticas."""
    TIPOS = [
        ('creacion', _('Acto de creación')),
        ('plan_desarrollo', _('Plan de Desarrollo y Fortalecimiento')), ('informe_anual', _('Informe anual')),
        ('evaluacion', _('Evaluación integral')), ('acta_comite', _('Acta del comité técnico-científico')),
        ('reglamento', _('Reglamento o normativa')), ('etica', _('Ética e integridad científica')),
        ('politica_datos', _('Política de datos y confidencialidad')),
        ('propiedad_intelectual', _('Propiedad intelectual')), ('seguridad', _('Seguridad y protocolos')),
        ('proyecto', _('Proyecto o estudio de factibilidad')), ('otro', _('Otro documento')),
    ]
    GOBIERNO = ('plan_desarrollo', 'informe_anual', 'evaluacion', 'acta_comite')
    NORMATIVA = ('creacion', 'reglamento', 'etica', 'politica_datos', 'propiedad_intelectual', 'seguridad')
    ESTADOS_DOCUMENTALES = [('informativo', _('Material informativo')), ('borrador', _('Borrador por revisar')),
                            ('aprobado', _('Documento aprobado'))]
    estado_documental = models.CharField(_('Estado documental'), max_length=12, choices=ESTADOS_DOCUMENTALES,
                                         default='informativo')
    emisor = models.CharField(_('Órgano o autoridad emisora'), max_length=200, blank=True)
    version = models.CharField(_('Versión'), max_length=60, blank=True)

    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='documentos', verbose_name=_('Centro'))
    tipo = models.CharField(_('Tipo'), max_length=22, choices=TIPOS)
    titulo = models.CharField(_('Título'), max_length=200)
    periodo = models.CharField(_('Periodo o fecha'), max_length=60, blank=True)
    resumen = models.TextField(_('Resumen'), blank=True)
    archivo = models.FileField(_('Archivo'), upload_to='centros_id/documentos/', blank=True)
    enlace = models.URLField(_('Enlace'), blank=True)
    publico = models.BooleanField(_('Público'), default=True,
                                  help_text=_('Las actas y lo interno se dejan sin publicar: solo los ve quien gestiona.'))
    fecha = models.DateField(_('Fecha'), null=True, blank=True)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)

    def clean(self):
        super().clean()
        if self.estado_documental == 'aprobado' and not all((self.emisor.strip(), self.fecha, self.fuente_validacion.strip())):
            raise ValidationError(_('Un documento aprobado requiere emisor, fecha y referencia institucional.'))

    class Meta:
        verbose_name = _('Documento del centro')
        verbose_name_plural = _('Documentos del centro')
        ordering = ('centro', 'orden', '-fecha')

    def __str__(self):
        return self.titulo

    @property
    def url(self):
        if self.archivo:
            from django.urls import reverse
            return reverse('archivo_centro_id', kwargs={'slug': self.centro.slug, 'tipo': 'documento', 'pk': self.pk})
        return self.enlace

    @property
    def es_pdf(self):
        return bool(self.archivo) and self.archivo.name.lower().endswith('.pdf')

    @property
    def icono(self):
        if self.es_pdf:
            return 'fas fa-file-pdf'
        return {'plan_desarrollo': 'fas fa-map', 'informe_anual': 'fas fa-chart-line', 'evaluacion': 'fas fa-clipboard-check',
                'acta_comite': 'fas fa-gavel', 'reglamento': 'fas fa-balance-scale', 'etica': 'fas fa-hand-holding-heart',
                'politica_datos': 'fas fa-user-shield', 'propiedad_intelectual': 'fas fa-certificate',
                'seguridad': 'fas fa-hard-hat', 'proyecto': 'fas fa-drafting-compass'}.get(self.tipo, 'fas fa-file-alt')


class AjusteSeccion(models.Model):
    """El nombre propio y la visibilidad que un centro da a una sección del mapa común."""
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='ajustes', verbose_name=_('Centro'))
    clave = models.CharField(_('Sección'), max_length=40)
    titulo = models.CharField(_('Nombre propio'), max_length=120, blank=True)
    oculta = models.BooleanField(_('Oculta'), default=False)

    class Meta:
        verbose_name = _('Ajuste de sección')
        verbose_name_plural = _('Ajustes de las secciones')
        constraints = [models.UniqueConstraint(fields=('centro', 'clave'), name='ajuste_seccion_por_centro')]

    def __str__(self):
        return f'{self.clave}: {self.titulo or "—"}{" (oculta)" if self.oculta else ""}'


class CarpetaCentro(models.Model):
    """Contenido propio del centro: una carpeta dentro de una sección o una sección nueva de una pestaña."""
    VISIBILIDADES = [('publica', _('Pública')), ('interna', _('Solo quien gestiona el centro'))]

    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='carpetas', verbose_name=_('Centro'))
    pestana = models.CharField(_('Pestaña'), max_length=40)
    seccion = models.CharField(_('Sección'), max_length=40, blank=True,
                               help_text=_('Vacío: la carpeta es una sección nueva de la pestaña.'))
    nombre = models.CharField(_('Nombre'), max_length=120)
    descripcion = models.CharField(_('Descripción'), max_length=255, blank=True)
    icono = models.CharField(_('Ícono'), max_length=40, default='fas fa-folder-open')
    visibilidad = models.CharField(_('Visibilidad'), max_length=8, choices=VISIBILIDADES, default='publica')
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)
    activa = models.BooleanField(_('Activa'), default=True)

    class Meta:
        verbose_name = _('Carpeta de contenido')
        verbose_name_plural = _('Carpetas de contenido')
        ordering = ('centro', 'pestana', 'orden', 'nombre')

    def __str__(self):
        return self.nombre


class RecursoCentro(models.Model):
    """Lo que hay dentro de una carpeta: un archivo, un enlace, un video o un texto."""
    TIPOS = [('archivo', _('Archivo')), ('enlace', _('Enlace')), ('video', _('Video de YouTube')), ('texto', _('Texto'))]

    carpeta = models.ForeignKey(CarpetaCentro, on_delete=models.CASCADE, related_name='recursos', verbose_name=_('Carpeta'))
    tipo = models.CharField(_('Tipo'), max_length=8, choices=TIPOS, default='archivo')
    titulo = models.CharField(_('Título'), max_length=160)
    descripcion = models.CharField(_('Descripción'), max_length=255, blank=True)
    archivo = models.FileField(_('Archivo'), upload_to='centros_id/recursos/', blank=True)
    url = models.URLField(_('Enlace o video'), blank=True)
    texto = models.TextField(_('Texto'), blank=True)
    orden = models.PositiveSmallIntegerField(_('Orden'), default=0)
    activo = models.BooleanField(_('Activo'), default=True)

    class Meta:
        verbose_name = _('Recurso')
        verbose_name_plural = _('Recursos')
        ordering = ('carpeta', 'orden', 'titulo')

    def __str__(self):
        return self.titulo

    def clean(self):
        if self.tipo == 'archivo' and not self.archivo:
            raise ValidationError({'archivo': _('Sube el archivo.')})
        if self.tipo in ('enlace', 'video') and not self.url:
            raise ValidationError({'url': _('Indica el enlace.')})
        if self.tipo == 'texto' and not self.texto:
            raise ValidationError({'texto': _('Escribe el texto.')})

    @property
    def archivo_url(self):
        if not self.archivo:
            return ''
        from django.urls import reverse
        return reverse('archivo_centro_id', kwargs={'slug': self.carpeta.centro.slug, 'tipo': 'recurso', 'pk': self.pk})

    @property
    def es_pdf(self):
        return bool(self.archivo) and self.archivo.name.lower().endswith('.pdf')

    @property
    def video_id(self):
        """El identificador de YouTube a partir de cualquiera de sus formas de enlace."""
        if self.tipo != 'video' or not self.url:
            return ''
        url = self.url
        for marca in ('v=', 'youtu.be/', 'embed/', 'shorts/'):
            if marca in url:
                return url.split(marca, 1)[1].split('&')[0].split('?')[0].split('/')[0]
        return ''


class SolicitudCentro(models.Model):
    """Un reto, una solicitud de servicio o un pedido de acceso a una capacidad: la puerta de entrada del centro.

    Sigue la ruta de atención del centro (registro, evaluación, aprobación, ejecución, entrega, cierre). Un Centro I+D
    no es un espacio reservable: el acceso a una de sus áreas se pide para un proyecto, una práctica o un servicio y
    es el centro quien lo evalúa y confirma el área y el horario.
    """
    objects = GestorIdentidades()
    TIPOS = [
        ('reto', _('Reto o proyecto de innovación')),
        ('servicio', _('Servicio tecnológico')),
        ('uso', _('Acceso a una capacidad del centro')),
        ('capacitacion', _('Capacitación o curso')),
        ('visita', _('Visita técnica o demostración')),
        ('asesoria', _('Acompañamiento o asesoría')),
    ]
    ESTADOS = [
        ('recibida', _('Recibida')),
        ('evaluacion', _('En evaluación técnica')),
        ('aprobada', _('Aprobada y planificada')),
        ('ejecucion', _('En ejecución')),
        ('entregada', _('Entregada')),
        ('cerrada', _('Cerrada')),
        ('no_procede', _('No procede')),
        ('cancelada', _('Cancelada')),
    ]
    PERFILES = [('interno', _('Comunidad universitaria')), ('externo', _('Empresa, GAD, asociación u otra institución'))]
    PRIORIDADES = [('alta', _('Alta')), ('media', _('Media')), ('baja', _('Baja'))]
    # Desde cada estado, a cuáles se puede pasar: la ruta no salta pasos ni vuelve atrás sin razón.
    SIGUIENTES = {
        'recibida': ('evaluacion', 'no_procede', 'cancelada'),
        'evaluacion': ('aprobada', 'no_procede', 'cancelada'),
        'aprobada': ('ejecucion', 'no_procede', 'cancelada'),
        'ejecucion': ('entregada', 'cancelada'),
        'entregada': ('cerrada',),
        'cerrada': (),
        'no_procede': (),
        'cancelada': (),
    }

    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='solicitudes', verbose_name=_('Centro'))
    usuario = ReferenciaCuenta(CuentaCentro, on_delete=models.PROTECT, related_name='solicitudes_centros_id',
                                verbose_name=_('Solicitante'))
    proyecto = models.ForeignKey(Proyecto, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes',
                                 verbose_name=_('Proyecto relacionado'))
    desarrollo = models.ForeignKey(Resultado, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes',
                                   verbose_name=_('Resultado o desarrollo relacionado'))
    finalidad = models.CharField(_('Finalidad de la colaboración'), max_length=16, blank=True,
                                 choices=[('colaboracion', _('Colaboración en investigación')), ('codesarrollo', _('Codesarrollo')),
                                          ('demostracion', _('Demostración')), ('transferencia', _('Consulta sobre transferencia'))])
    tipo = models.CharField(_('Qué necesita'), max_length=12, choices=TIPOS, default='servicio')
    perfil = models.CharField(_('Quién lo pide'), max_length=8, choices=PERFILES, default='interno')
    institucion = models.CharField(_('Carrera, unidad o institución'), max_length=160, blank=True)
    titulo = models.CharField(_('Nombre del reto o la solicitud'), max_length=160)
    problema = models.TextField(_('Problema o necesidad'))
    resultado_esperado = models.CharField(_('Resultado esperado'), max_length=255)
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='solicitudes', verbose_name=_('Servicio del portafolio'))
    componente = models.ForeignKey(Componente, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='solicitudes', verbose_name=_('Área'))
    zona = models.ForeignKey(Zona, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes',
                             verbose_name=_('Área del centro a la que se accede'))
    equipo = models.ForeignKey(EquipoCentro, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes',
                               verbose_name=_('Equipo individual'))
    inicio_preferido = models.DateTimeField(_('Inicio solicitado'), null=True, blank=True)
    fin_preferido = models.DateTimeField(_('Fin solicitado'), null=True, blank=True)
    requisitos_validados = models.BooleanField(_('Requisitos de acceso comprobados'), default=False)
    evidencia_requisitos = models.CharField(_('Referencia privada de comprobación'), max_length=500, blank=True)
    supervisor = models.ForeignKey(Integrante, on_delete=models.SET_NULL, null=True, blank=True, related_name='usos_supervisados')
    responsable_atencion = models.ForeignKey(Integrante, on_delete=models.SET_NULL, null=True, blank=True, related_name='casos_atendidos')
    diagnostico = models.TextField(_('Diagnóstico compartido con el solicitante'), blank=True)
    plan = models.TextField(_('Plan y compromisos de atención'), blank=True)
    evaluacion_cierre = models.TextField(_('Evaluación y motivo del cierre'), blank=True)
    notas_internas = models.TextField(_('Notas internas reservadas'), blank=True)
    fecha_preferida = models.DateField(_('Fecha preferida'), null=True, blank=True)
    participantes = models.PositiveSmallIntegerField(_('Participantes'), null=True, blank=True)
    prioridad = models.CharField(_('Prioridad'), max_length=5, choices=PRIORIDADES, blank=True)
    estado = models.CharField(_('Estado'), max_length=10, choices=ESTADOS, default='recibida')
    inicio_reservado = models.DateTimeField(_('Inicio confirmado'), null=True, blank=True)
    fin_reservado = models.DateTimeField(_('Fin confirmado'), null=True, blank=True)
    respuesta = models.TextField(_('Respuesta del centro'), blank=True)
    entregable = models.CharField(_('Qué se entregó'), max_length=255, blank=True)
    creada = models.DateTimeField(_('Recibida'), auto_now_add=True)
    actualizada = models.DateTimeField(_('Actualizada'), auto_now=True)
    cerrada_en = models.DateTimeField(_('Cerrada'), null=True, blank=True)

    class Meta:
        verbose_name = _('Solicitud')
        verbose_name_plural = _('Solicitudes')
        ordering = ('-creada',)
        indexes = [
            models.Index(fields=('centro', 'estado', '-creada'), name='cid_solic_centro_estado_idx'),
            models.Index(fields=('centro', 'usuario', '-creada'), name='cid_solic_centro_usuario_idx'),
        ]

    def __str__(self):
        return f'{self.titulo} · {self.get_estado_display()}'

    def clean(self):
        super().clean()
        for campo in ('proyecto', 'desarrollo', 'servicio', 'componente', 'supervisor', 'responsable_atencion'):
            relacionado = getattr(self, campo, None)
            if relacionado and self.centro_id and relacionado.centro_id != self.centro_id:
                raise ValidationError({campo: _('El registro debe pertenecer al mismo centro.')})
        if self.proyecto_id and self.desarrollo_id and self.desarrollo.proyecto_id not in (None, self.proyecto_id):
            raise ValidationError({'desarrollo': _('El desarrollo corresponde a otro proyecto.')})
        if self.inicio_reservado and self.fin_reservado and self.fin_reservado <= self.inicio_reservado:
            raise ValidationError({'fin_reservado': _('El acceso debe terminar después de empezar.')})
        if self.zona_id and self.centro_id and self.zona.centro_id != self.centro_id:
            raise ValidationError({'zona': _('El área debe ser del mismo centro.')})
        from .operaciones import validar_solicitud
        validar_solicitud(self)

    def avanzar(self, estado):
        """Pasa al estado siguiente de la ruta; el cierre deja constancia de cuándo se cerró."""
        if estado not in self.SIGUIENTES[self.estado]:
            raise ValidationError(_('La solicitud no puede pasar de «%(actual)s» a ese estado.')
                                  % {'actual': self.get_estado_display()})
        self.estado = estado
        if estado in ('cerrada', 'no_procede', 'cancelada'):
            self.cerrada_en = timezone.now()


    @property
    def referencia(self):
        return f'{self.centro.sigla}-{self.pk:06d}' if self.pk else ''

    @property
    def puede_retirar(self):
        return self.estado in ('recibida', 'evaluacion', 'aprobada')

    def save(self, *args, **kwargs):
        from .operaciones import guardar_solicitud
        actor = kwargs.pop('actor', None)
        motivo = kwargs.pop('motivo', '')
        if kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = set(kwargs['update_fields']) | {'cerrada_en', 'actualizada'}
        return guardar_solicitud(self, lambda: super(SolicitudCentro, self).save(*args, **kwargs), actor, motivo)


class HorarioRecurso(models.Model):
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE)
    zona = models.ForeignKey(Zona, on_delete=models.CASCADE, null=True, blank=True, related_name='horarios')
    equipo = models.ForeignKey(EquipoCentro, on_delete=models.CASCADE, null=True, blank=True, related_name='horarios')
    dia = models.PositiveSmallIntegerField(_('Día de la semana'), choices=list(enumerate(
        ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'])))
    abre = models.TimeField(_('Abre'))
    cierra = models.TimeField(_('Cierra'))

    class Meta:
        ordering = ('dia', 'abre')
        verbose_name_plural = _('Horarios de recursos')
        constraints = [models.CheckConstraint(condition=(models.Q(zona__isnull=False, equipo__isnull=True)
                        | models.Q(zona__isnull=True, equipo__isnull=False)), name='cid_horario_un_recurso')]

    def __str__(self):
        return f'{self.zona or self.equipo} · {self.get_dia_display()} {self.abre}–{self.cierra}'

    def clean(self):
        from .operaciones import validar_recurso
        validar_recurso(self)
        if self.abre and self.cierra and self.cierra <= self.abre:
            raise ValidationError(_('El cierre debe ser posterior a la apertura.'))
        if self.abre and self.cierra and HorarioRecurso.objects.filter(zona_id=self.zona_id, equipo_id=self.equipo_id,
                dia=self.dia, abre__lt=self.cierra, cierra__gt=self.abre).exclude(pk=self.pk).exists():
            raise ValidationError(_('El horario se cruza con otra ventana del mismo recurso.'))

    def save(self, *args, **kwargs):
        from .operaciones import guardar_regla
        return guardar_regla(self, lambda: super(HorarioRecurso, self).save(*args, **kwargs))


class BloqueoRecurso(models.Model):
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE)
    zona = models.ForeignKey(Zona, on_delete=models.CASCADE, null=True, blank=True, related_name='bloqueos')
    equipo = models.ForeignKey(EquipoCentro, on_delete=models.CASCADE, null=True, blank=True, related_name='bloqueos')
    inicio = models.DateTimeField(_('Desde'))
    fin = models.DateTimeField(_('Hasta'))
    motivo = models.CharField(_('Motivo interno'), max_length=255)

    class Meta:
        ordering = ('inicio',)
        verbose_name_plural = _('Bloqueos de recursos')
        constraints = [models.CheckConstraint(condition=(models.Q(zona__isnull=False, equipo__isnull=True)
                        | models.Q(zona__isnull=True, equipo__isnull=False)), name='cid_bloqueo_un_recurso')]

    def __str__(self):
        return f'{self.zona or self.equipo} · {self.inicio}'

    def clean(self):
        from .operaciones import validar_recurso
        validar_recurso(self)
        if self.inicio and self.fin and self.fin <= self.inicio:
            raise ValidationError(_('El bloqueo debe terminar después de empezar.'))

    def save(self, *args, **kwargs):
        from .operaciones import guardar_regla
        return guardar_regla(self, lambda: super(BloqueoRecurso, self).save(*args, **kwargs))


class HabilitacionEquipo(models.Model):
    objects = GestorIdentidades()
    equipo = models.ForeignKey(EquipoCentro, on_delete=models.CASCADE, related_name='habilitaciones')
    usuario = ReferenciaCuenta(CuentaCentro, on_delete=models.PROTECT)
    desde = models.DateField(_('Válida desde'))
    hasta = models.DateField(_('Válida hasta'))
    evidencia = models.CharField(_('Respaldo de evaluación práctica o autorización'), max_length=500)
    verificador = ReferenciaCuenta(CuentaCentro, on_delete=models.PROTECT, related_name='+')
    revocada = models.BooleanField(_('Revocada'), default=False)

    class Meta:
        verbose_name_plural = _('Habilitaciones de equipos')

    def __str__(self):
        return f'{self.equipo} · {self.usuario}'

    def clean(self):
        if not self.evidencia.strip():
            raise ValidationError(_('Registre respaldo de la evaluación o autorización.'))
        if self.desde and self.hasta and self.hasta < self.desde:
            raise ValidationError(_('La habilitación termina antes de empezar.'))
        if self.verificador_id and self.equipo_id and not self.equipo.componente.centro.puede_gestionar(principal_vigente(self.verificador_id)):
            raise ValidationError(_('El verificador debe gestionar el centro.'))

    def save(self, *args, **kwargs):
        with transaction.atomic(using=alias_centros(self)):
            list(EquipoCentro.objects.select_for_update().filter(pk=self.equipo_id))
            self.full_clean()
            return super().save(*args, **kwargs)


class RegistroSolicitud(models.Model):
    objects = GestorIdentidades()
    solicitud = models.ForeignKey(SolicitudCentro, on_delete=models.CASCADE, related_name='historial')
    fecha = models.DateTimeField(auto_now_add=True)
    autor = ReferenciaCuenta(CuentaCentro, on_delete=models.PROTECT, null=True, blank=True)
    estado_anterior = models.CharField(max_length=10, blank=True)
    estado_nuevo = models.CharField(max_length=10)
    detalle = models.TextField(_('Detalle compartido'))

    class Meta:
        ordering = ('fecha', 'pk')
        verbose_name_plural = _('Historial de solicitudes')

    @property
    def estado_legible(self):
        return dict(SolicitudCentro.ESTADOS).get(self.estado_nuevo, self.estado_nuevo)

    @property
    def origen_legible(self):
        if self.autor_id == self.solicitud.usuario_id:
            return _('Solicitante')
        return _('Centro') if self.autor_id else _('Registro del sistema')


class SesionAcompanamiento(models.Model):
    solicitud = models.ForeignKey(SolicitudCentro, on_delete=models.CASCADE, related_name='sesiones')
    responsable = models.ForeignKey(Integrante, on_delete=models.PROTECT, related_name='sesiones_acompanamiento')
    inicio = models.DateTimeField(_('Inicio'))
    fin = models.DateTimeField(_('Fin'))
    modalidad = models.CharField(_('Modalidad y lugar o medio'), max_length=200)
    estado = models.CharField(max_length=12, default='programada', choices=[('programada', _('Programada')),
                              ('realizada', _('Realizada')), ('cancelada', _('Cancelada'))])
    acuerdos = models.TextField(_('Acuerdos compartidos'), blank=True)
    notas_internas = models.TextField(_('Notas reservadas'), blank=True)

    class Meta:
        ordering = ('inicio', 'pk')
        verbose_name_plural = _('Sesiones de acompañamiento')

    def __str__(self):
        return f'{self.solicitud.referencia} · {self.inicio}'

    def clean(self):
        from .operaciones import validar_sesion
        validar_sesion(self)

    def save(self, *args, **kwargs):
        actor = kwargs.pop('actor', None)
        with transaction.atomic(using=alias_centros(self)):
            self.solicitud = SolicitudCentro.objects.select_for_update().get(pk=self.solicitud_id)
            list(Integrante.objects.select_for_update().filter(pk=self.responsable_id))
            self.full_clean()
            resultado = super().save(*args, **kwargs)
            RegistroSolicitud.objects.create(solicitud=self.solicitud, autor=identidad_de(actor) if actor is not None else None,
                estado_anterior=self.solicitud.estado, estado_nuevo=self.solicitud.estado,
                detalle=f'Sesión {self.get_estado_display().lower()}: {timezone.localtime(self.inicio):%d/%m/%Y %H:%M}.')
            return resultado


class TareaSolicitud(models.Model):
    solicitud = models.ForeignKey(SolicitudCentro, on_delete=models.CASCADE, related_name='tareas')
    titulo = models.CharField(_('Compromiso'), max_length=200)
    a_cargo = models.CharField(max_length=12, choices=[('solicitante', _('Solicitante')), ('centro', _('Centro'))])
    plazo = models.DateField(_('Fecha límite'))
    completada = models.BooleanField(_('Cumplida'), default=False)
    evidencia = models.CharField(_('Resultado o evidencia compartida'), max_length=500, blank=True)

    class Meta:
        ordering = ('plazo', 'pk')
        verbose_name_plural = _('Compromisos de atención')

    def clean(self):
        if self.completada and not self.evidencia.strip():
            raise ValidationError(_('Un compromiso cumplido requiere evidencia.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class HerramientaCentro(models.Model):
    objects = GestorIdentidades()
    centro = models.ForeignKey(CentroID, on_delete=models.CASCADE, related_name='herramientas')
    nombre = models.CharField(max_length=160)
    tipo = models.CharField(max_length=16, choices=[('calculadora', _('Calculadora')), ('educativa', _('Simulación educativa')),
                            ('ingenieria', _('Simulación de ingeniería')), ('entorno', _('Entorno virtual')),
                            ('recorrido', _('Recorrido virtual'))])
    objetivo = models.TextField()
    entradas = models.TextField(_('Entradas, unidades y rangos'))
    metodo = models.TextField(_('Método y fuentes'))
    salidas = models.TextField(_('Salidas y unidades'))
    supuestos = models.TextField(_('Supuestos'))
    limites = models.TextField(_('Validación y limitaciones'))
    version = models.CharField(max_length=80)
    enlace = models.URLField()
    publicado = models.BooleanField(default=False)
    validado_en = models.DateTimeField(null=True, blank=True, editable=False)
    validado_por = ReferenciaCuenta(CuentaCentro, on_delete=models.PROTECT, null=True, blank=True, editable=False)

    class Meta:
        verbose_name_plural = _('Herramientas de simulación y entornos')

    def __str__(self):
        return self.nombre

    @property
    def visible(self):
        return bool(self.publicado and self.validado_en and self.validado_por_id)

    def validar(self, usuario):
        if not self.centro.puede_gestionar(usuario):
            raise ValidationError(_('Solo la gestión del centro puede validar la herramienta.'))
        self.full_clean()
        self.validado_en, self.validado_por = timezone.now(), usuario
        # Se persiste la revisión después de detectar cambios del contenido anterior.
        self.save(_validando=True)

    def save(self, *args, **kwargs):
        validando = kwargs.pop('_validando', False)
        if self.pk and not validando:
            campos = ('nombre', 'tipo', 'objetivo', 'entradas', 'metodo', 'salidas', 'supuestos', 'limites', 'version', 'enlace')
            anterior = type(self).objects.filter(pk=self.pk).values(*campos).first()
            if anterior and any(anterior[c] != getattr(self, c) for c in campos):
                self.validado_en, self.validado_por = None, None
                if kwargs.get('update_fields') is not None:
                    kwargs['update_fields'] = set(kwargs['update_fields']) | {'validado_en', 'validado_por'}
        return super().save(*args, **kwargs)
