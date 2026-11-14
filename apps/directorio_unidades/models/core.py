from apps.core.presentation.tipologias import nombre_tipologia


from apps.core.presentation.tipologias import tipologia as tipologia_por_codigo


from django.conf import settings


from django.contrib.auth import get_user_model


from django.contrib.auth.models import Group, Permission


from django.db import models


from django.db.models.signals import m2m_changed


from django.dispatch import receiver


from urllib.parse import parse_qs, urlparse


from django.contrib.auth.models import User


from django.core.exceptions import ValidationError


from django.core.validators import MaxValueValidator, MinValueValidator


from django.templatetags.static import static


from django.utils.text import slugify


from apps.directorio_unidades.models.mapa import PuntoEnMapa


class ClasificacionInstitucional(models.Model):
    """Catalogo administrable: codigo estable, orden, archivado y alcance.

    El codigo identifica la clasificacion en filtros y enlaces publicos y no
    cambia al renombrarla. Archivar la retira de filtros y de unidades nuevas
    sin tocar las unidades que ya la tienen. `tipologias` lista los codigos de
    tipologia donde se ofrece; vacio significa todas.
    """

    codigo = models.SlugField(
        "Código",
        max_length=100,
        unique=True,
        blank=True,
        help_text="Identificador estable generado del nombre; se usa en los filtros públicos y no cambia.",
    )
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    orden = models.PositiveSmallIntegerField("Orden", default=100)
    activa = models.BooleanField(
        "Activa",
        default=True,
        help_text="Una clasificación archivada deja de ofrecerse en filtros y unidades nuevas; las unidades que ya la tienen la conservan.",
    )
    tipologias = models.JSONField(
        "Tipologías",
        default=list,
        blank=True,
        help_text="Códigos de tipología donde se ofrece; vacío significa todas.",
    )

    class Meta:
        abstract = True
        ordering = ("orden", "nombre")

    def __str__(self):
        return self.nombre

    def aplica_a(self, dependencia):
        return not self.tipologias or dependencia in self.tipologias

    def clean(self):
        super().clean()
        if not isinstance(self.tipologias, list) or any(
            not isinstance(codigo, str) or tipologia_por_codigo(codigo) is None
            for codigo in self.tipologias
        ):
            raise ValidationError(
                {
                    "tipologias": "Las tipologías deben ser códigos del catálogo institucional.",
                }
            )

    def _codigo_unico(self):
        base = slugify(self.nombre)[:90] or "clasificacion"
        candidato, sufijo = base, 2
        existentes = (
            type(self).objects.exclude(pk=self.pk)
            if self.pk
            else type(self).objects.all()
        )
        while existentes.filter(codigo=candidato).exists():
            candidato = f"{base}-{sufijo}"
            sufijo += 1
        return candidato

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self._codigo_unico()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.unidades.exists():
            raise ValidationError(
                "Archiva la clasificación en lugar de eliminarla: hay unidades que la usan."
            )
        super().delete(*args, **kwargs)


class Categoria(ClasificacionInstitucional):
    """Subarea de conocimiento de una unidad."""

    class Meta(ClasificacionInstitucional.Meta):
        db_table = "webcitt_categoria"
        verbose_name = "Subárea"
        verbose_name_plural = "Subáreas"


class TipoLaboratorio(ClasificacionInstitucional):
    """Modo de uso de una unidad: docencia, investigación, innovación, servicios."""

    class Meta(ClasificacionInstitucional.Meta):
        db_table = "webcitt_tipolaboratorio"
        verbose_name = "Modo de uso"
        verbose_name_plural = "Modos de uso"


class DependenciaAcademica(models.Model):
    """El decanato o la dependencia a la que está adscrita una unidad.

    Designa al responsable de cada una de sus unidades y recibe el informe de
    cumplimiento que la Dirección emite, para decidir lo que le toca: cambiar
    responsables, comprar equipamiento, repotenciar o rediseñar la unidad. No
    firma las entregas: quien las valida es el responsable que ella nombró, y
    quien dice si la unidad cumple es la Dirección.
    """

    TIPOS = [
        ("decanato", "Decanato"),
        ("direccion", "Dirección"),
        ("vicerrectorado", "Vicerrectorado"),
        ("otra", "Otra dependencia"),
    ]

    nombre = models.CharField(max_length=220, unique=True)
    tipo = models.CharField(max_length=16, choices=TIPOS, default="decanato")
    activa = models.BooleanField(default=True)
    centro_costo = models.CharField(
        'Centro de costo agrupador', max_length=220, blank=True,
        help_text='Denominación confirmada para la matriz universitaria de compras. '
                  'La dependencia administra este centro y ejecuta las adquisiciones autorizadas.',
    )
    receptores = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        db_table="webcitt_dependenciaacademica_receptores",
        blank=True,
        related_name="dependencias_que_recibe",
        verbose_name="Quiénes reciben el informe",
        help_text="Reciben el informe de cumplimiento de sus unidades y designan a sus responsables.",
    )

    class Meta:
        db_table = "webcitt_dependenciaacademica"
        ordering = ["nombre"]
        verbose_name = "Dependencia académica"
        verbose_name_plural = "Dependencias académicas"

    def __str__(self):
        return self.nombre

    def recibe_informe(self, usuario):
        return self.activa and self.receptores.filter(pk=usuario.pk).exists()


@receiver(m2m_changed, sender=DependenciaAcademica.receptores.through)
def habilitar_receptor(sender, instance, action, pk_set, **kwargs):
    """Nombrar a quien recibe el informe le da lo que necesita para leerlo, y nada más.

    Entra al administrador para designar a los responsables de las unidades de
    su dependencia y para leer su cumplimiento; lo que puede tocar lo acota
    cada pantalla, no un permiso global.
    """
    if action != "post_add" or not pk_set:
        return
    grupo, _ = Group.objects.get_or_create(name="Recepción de informes de calidad")
    grupo.permissions.add(
        *Permission.objects.filter(
            content_type__app_label__in=("directorio_unidades", "documentos"),
            codename__in=(
                "view_dependenciaacademica",
                "change_dependenciaacademica",
                "view_documentoexpediente",
            ),
        )
    )
    for usuario in get_user_model().objects.filter(pk__in=pk_set):
        if not usuario.is_staff:
            usuario.is_staff = True
            usuario.save(update_fields=["is_staff"])
        usuario.groups.add(grupo)


class Unidad(PuntoEnMapa):
    # Limite institucional de clasificacion; lo aplican el modelo y el
    # formulario del admin, que es donde llegan las categorias enviadas.
    MAXIMO_CATEGORIAS = 6

    # La tipologia (dependencia) es un catalogo institucional administrable;
    # los mapas siguientes describen las cuatro bases operativas implementadas
    # y se consultan por la base de cada tipologia.
    CLASIFICACION_FUNCIONAL_CHOICES = [
        ("laboratorio_academico", "Laboratorio académico"),
        ("laboratorio_id", "Laboratorio de I+D"),
        ("laboratorio_mixto", "Laboratorio académico y de I+D"),
        ("planta_piloto", "Planta piloto"),
        ("centro_experimental", "Centro experimental"),
        ("observatorio", "Observatorio"),
        ("plataforma_tecnologica", "Plataforma tecnológica"),
    ]

    CLASIFICACIONES_POR_DEPENDENCIA = {
        "laboratorios": {
            "laboratorio_academico",
            "laboratorio_id",
            "laboratorio_mixto",
            "plataforma_tecnologica",
        },
        "plantas_piloto": {"planta_piloto"},
        "centro_experimental": {"centro_experimental"},
        "observatorios": {"observatorio"},
    }

    CLASIFICACION_PREDETERMINADA = {
        "laboratorios": "laboratorio_academico",
        "plantas_piloto": "planta_piloto",
        "centro_experimental": "centro_experimental",
        "observatorios": "observatorio",
    }

    MODO_OPERACION_CHOICES = [
        ("lotes", "Producción por lotes"),
        ("continuo", "Flujo continuo"),
        ("celda", "Celda de producción"),
        ("mixto", "Operación mixta"),
    ]
    ESTADO_CATALOGO_CHOICES = [
        ("disponible", "Disponible"),
        ("reserva_previa", "Con reserva previa"),
        ("mantenimiento", "En mantenimiento"),
        ("en_creacion", "En creación: pendiente de su resolución"),
    ]

    AREA_CONOCIMIENTO_CHOICES = [
        ("ingenieria", "Ingeniería y Sistemas Productivos"),
        ("ia", "Inteligencia Artificial, Ciencia de Datos y Ciberseguridad"),
        ("biotecnologia", "Biotecnología y Ciencias Biológicas Aplicadas"),
        ("salud", "Ciencias de la Salud y Formación Clínica"),
        ("agro", "Agroindustria, Tecnologías de Alimentos y Sostenibilidad Productiva"),
        ("comunicacion", "Tecnologías Inmersivas, Comunicación y Medios Digitales"),
        ("gestion", "Gestión Empresarial, Comercio y Desarrollo Territorial"),
        ("Educacion", "Educación e Innovación Pedagógica"),
        ("formacion", "Formación Integral y Desarrollo Humano"),
        ("otro", "Otro"),
    ]

    nombre = models.CharField(max_length=200)
    nombre_corto = models.CharField(
        "Nombre corto",
        max_length=60,
        blank=True,
        help_text="Cómo se la llama a diario, por ejemplo «FabLab UPEC». Acompaña al nombre oficial "
        "en la ficha y en el catálogo.",
    )
    descripcion = models.TextField()
    fecha_inicio = models.DateField()
    visitas = models.PositiveIntegerField(default=0)
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    fecha_fin = models.DateField(blank=True, null=True)
    categorias = models.ManyToManyField(
        "directorio_unidades.Categoria",
        db_table="webcitt_unidad_categorias",
        blank=True,
        related_name="unidades",
        help_text="Puede seleccionar hasta 6 categorías.",
    )
    tipos_laboratorio = models.ManyToManyField(
        "directorio_unidades.TipoLaboratorio",
        db_table="webcitt_unidad_tipos_laboratorio",
        blank=True,
        related_name="unidades",
        help_text="Seleccione los tipos de laboratorio (puede ser múltiple).",
    )
    activo = models.BooleanField(default=True)
    # Quien responde por la unidad ante la Universidad. Es personal de la
    # unidad con todos los permisos y el único que puede cambiar su personal.
    administrador = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unidades_administradas",
        help_text="Usuario administrador asignado a la unidad",
    )
    imagen = models.ImageField(
        "Imagen de portada",
        upload_to="proyectos_imagenes/",
        blank=True,
        null=True,
        help_text=(
            "Fotografía horizontal propia de la unidad para el catálogo. "
            "Si se omite, se muestra la portada institucional genérica."
        ),
    )
    # Una foto con licencia abierta (Creative Commons) exige citar autor, licencia y fuente donde se muestra.
    credito_imagen = models.CharField(
        "Crédito de la imagen",
        max_length=255,
        blank=True,
        help_text="Título, autor y licencia si la foto no es propia, por ejemplo «Laguna del Voladero · Autor · CC BY-SA 4.0».",
    )
    credito_imagen_url = models.URLField(
        "Fuente de la imagen",
        max_length=500,
        blank=True,
        help_text="La página del archivo, donde se leen su autor y su licencia.",
    )
    video_unidad = models.URLField(
        "Video de presentación de la unidad",
        blank=True,
        max_length=500,
        help_text=(
            "Enlace de YouTube para la presentación pública de esta unidad. "
            "Si se omite, se conserva el video institucional."
        ),
    )
    plano_espacios = models.ImageField(
        "Plano o layout de los espacios",
        upload_to="unidades/planos_espacios/",
        blank=True,
        null=True,
        help_text=(
            "Imagen general con la distribución de áreas, estaciones, accesos "
            "y zonas de circulación de la unidad."
        ),
    )
    recorrido_espacios_youtube_url = models.URLField(
        "Video de recorrido por los espacios",
        blank=True,
        max_length=500,
        help_text="Enlace de YouTube del recorrido público por las áreas de la unidad.",
    )
    recorrido_360_ruta = models.CharField(
        "Tour 360°",
        blank=True,
        max_length=500,
        help_text=(
            "URL https:// o ruta relativa dentro de archivos estáticos, por ejemplo "
            "img/360/laboratorio/index.html. Si la unidad carga en sus recursos el ZIP del recorrido "
            "(tipo «Recorrido 360°»), el visor usa ese."
        ),
    )
    descripcion_corta = models.CharField(max_length=255, blank=True, null=True)
    likes = models.PositiveIntegerField(default=0)
    slug = models.SlugField(max_length=100, unique=True, null=True)
    dependencia = models.CharField(
        max_length=50, blank=True, null=True, help_text="Seleccione el tipo de unidad."
    )
    clasificacion_funcional = models.CharField(
        "Clasificación funcional",
        max_length=40,
        choices=CLASIFICACION_FUNCIONAL_CHOICES,
        blank=True,
        help_text=(
            "Define la finalidad predominante y el flujo operativo de la unidad. "
            "No modifica su catálogo o URL pública."
        ),
    )
    modo_operacion = models.CharField(
        "Modo de operación",
        max_length=20,
        choices=MODO_OPERACION_CHOICES,
        blank=True,
        help_text="Forma principal en que trabaja la unidad. Es obligatoria para plantas piloto.",
    )
    estado_catalogo = models.CharField(
        "Disponibilidad en el catálogo",
        max_length=20,
        choices=ESTADO_CATALOGO_CHOICES,
        default="disponible",
        help_text="Estado público general de la unidad; no reemplaza la agenda ni el estado de cada equipo.",
    )
    area_conocimiento = models.CharField(
        max_length=50,
        choices=AREA_CONOCIMIENTO_CHOICES,
        blank=True,
        null=True,
        help_text="Seleccione el área de conocimiento de la unidad.",
    )
    codigo = models.CharField(
        "Código institucional",
        max_length=60,
        blank=True,
        help_text="Código interno de la unidad, por ejemplo LAB-FIACA-001.",
    )
    ubicacion = models.CharField(
        "Ubicación o espacio",
        max_length=255,
        blank=True,
        help_text="Edificio, bloque, piso, campus o referencia física.",
    )
    piso = models.SmallIntegerField(
        "Piso o nivel",
        null=True,
        blank=True,
        validators=[MinValueValidator(-5), MaxValueValidator(60)],
        help_text="0 es la planta baja y los subsuelos van en negativo. Ordena las unidades que comparten edificio.",
    )
    direccion = models.CharField(
        "Dirección",
        max_length=255,
        blank=True,
        help_text="Calle e intersección, ciudad y provincia, tal como se lee en el mapa.",
    )
    horario_atencion = models.CharField(
        "Horario de atención",
        max_length=160,
        blank=True,
        help_text="Ejemplo: lunes a viernes, 08:00–18:00.",
    )
    capacidad_personas = models.PositiveIntegerField(
        "Capacidad de personas",
        blank=True,
        null=True,
        help_text="Aforo o número recomendado de puestos de trabajo.",
    )
    contacto_email = models.EmailField(
        "Correo de contacto",
        blank=True,
        help_text="Correo público del responsable o de la unidad.",
    )
    telefono = models.CharField(
        "Teléfono",
        max_length=60,
        blank=True,
        help_text="Fijo de la unidad, con extensión si la tiene. Ejemplo: (06) 2980 302 ext. 2870.",
    )
    celular = models.CharField("Celular", max_length=30, blank=True)
    sitio_web = models.URLField("Página web", max_length=300, blank=True)
    resolucion_numero = models.CharField(
        "Número de la resolución de creación",
        max_length=80,
        blank=True,
        help_text="Ejemplo: Resolución 088-CU-2022. El documento se carga en el expediente.",
    )
    fecha_resolucion = models.DateField(
        "Fecha de la resolución de creación", null=True, blank=True
    )
    centro_vinculado = models.CharField(
        "Centro o dependencia vinculada",
        max_length=220,
        blank=True,
        help_text="Centro I+D, facultad o dependencia institucional asociada.",
    )
    facultad = models.CharField(
        "Facultad",
        max_length=220,
        blank=True,
        help_text="Facultad académica responsable o vinculada a la unidad.",
    )
    adscrita_a = models.ForeignKey(
        DependenciaAcademica,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unidades",
        verbose_name="Adscrita a",
        help_text="Decanato o dependencia que recibe los resultados evaluados por Dirección y gestiona sus compras.",
    )
    carreras = models.TextField(
        "Carrera o carreras vinculadas",
        blank=True,
        help_text="Registre una o varias carreras separadas por comas.",
    )

    def __str__(self):
        return self.nombre

    @property
    def tipologia(self):
        """Tipologia institucional vigente del codigo guardado, o None."""
        cache = getattr(self, "_tipologia_cache", None)
        if cache is None or cache[0] != self.dependencia:
            cache = (self.dependencia, tipologia_por_codigo(self.dependencia))
            self._tipologia_cache = cache
        return cache[1]

    @property
    def codigo_base(self):
        """Implementacion cuyo comportamiento reutiliza la unidad.

        Sin tipologia registrada conserva el codigo guardado, de modo que los
        mapas heredados resuelven igual que antes del catalogo administrable.
        """
        actual = self.tipologia
        return actual.base if actual else (self.dependencia or "")

    @property
    def nombre_tipologia(self):
        return nombre_tipologia(self.dependencia)

    @property
    def etiqueta_gestion(self):
        from django.utils.translation import gettext

        tipo = self.nombre_tipologia.lower() if self.tipologia else gettext('unidad')
        return gettext('Gestionar %(tipo)s') % {'tipo': tipo}

    def get_absolute_url(self):
        from django.urls import reverse

        if self.dependencia == "laboratorios":
            return reverse("laboratorio_detalle", kwargs={"slug": self.slug})
        elif self.dependencia == "observatorios":
            return reverse("observatorio_detalle", kwargs={"slug": self.slug})
        elif self.dependencia == "centro_experimental":
            return reverse("centro_experimental_detalle", kwargs={"slug": self.slug})
        elif self.dependencia == "plantas_piloto":
            return reverse("planta_piloto_detalle", kwargs={"slug": self.slug})
        return reverse("laboratorio_detalle", kwargs={"slug": self.slug})

    @property
    def recorrido_espacios_youtube_embed_url(self):
        """Normaliza enlaces públicos de YouTube para un iframe sin cookies."""
        video_id = self._youtube_video_id(self.recorrido_espacios_youtube_url)
        if not video_id:
            return ""
        return (
            f"https://www.youtube-nocookie.com/embed/{video_id}?rel=0&modestbranding=1"
        )

    @staticmethod
    def _youtube_video_id(value):
        """Extrae el identificador de las variantes públicas de URL de YouTube."""
        value = (value or "").strip()
        if not value:
            return ""
        parsed = urlparse(value)
        host = parsed.netloc.lower().removeprefix("www.")
        video_id = ""
        if host == "youtu.be":
            video_id = parsed.path.strip("/").split("/")[0]
        elif host in {"youtube.com", "m.youtube.com", "youtube-nocookie.com"}:
            if parsed.path == "/watch":
                video_id = parse_qs(parsed.query).get("v", [""])[0]
            elif parsed.path.startswith(("/embed/", "/shorts/")):
                video_id = parsed.path.rstrip("/").split("/")[-1]
        if not video_id:
            return ""
        return video_id

    @property
    def video_unidad_youtube_id(self):
        return self._youtube_video_id(self.video_unidad)

    @property
    def recorrido_360_public_url(self):
        value = (self.recorrido_360_ruta or "").strip()
        if not value:
            return ""
        if value.startswith(("https://", "http://", "/")):
            return value
        return static(value)

    @property
    def piso_texto(self):
        if self.piso is None:
            return ""
        if self.piso == 0:
            return "Planta baja"
        return f"Piso {self.piso}" if self.piso > 0 else f"Subsuelo {-self.piso}"

    @property
    def espacio_completo(self):
        """Edificio o espacio con su piso, como se lee en la ficha y en el mapa."""
        return " · ".join(
            parte for parte in (self.ubicacion.strip(), self.piso_texto) if parte
        )

    @property
    def direccion_completa(self):
        """Etiqueta del punto en el mapa: el espacio, su piso y la dirección postal."""
        return " · ".join(
            parte for parte in (self.espacio_completo, self.direccion.strip()) if parte
        )

    def clean(self):
        super().clean()
        if self.dependencia and self.tipologia is None:
            raise ValidationError(
                {
                    "dependencia": "La tipología de unidad no existe en el catálogo institucional.",
                }
            )
        clasificaciones_validas = self.CLASIFICACIONES_POR_DEPENDENCIA.get(
            self.codigo_base,
            set(),
        )
        if (
            self.clasificacion_funcional
            and clasificaciones_validas
            and self.clasificacion_funcional not in clasificaciones_validas
        ):
            raise ValidationError(
                {
                    "clasificacion_funcional": (
                        "La clasificación funcional no corresponde al tipo de unidad "
                        "seleccionado."
                    ),
                }
            )

        if self.codigo_base == "plantas_piloto" and not self.modo_operacion:
            raise ValidationError(
                {
                    "modo_operacion": "El modo de operación es obligatorio para una planta piloto.",
                }
            )

        # Evitar acceder a relaciones many-to-many antes de que la instancia
        # tenga un `pk` (esto ocurre durante la creación en el admin).
        if (
            getattr(self, "pk", None)
            and self.categorias.count() > self.MAXIMO_CATEGORIAS
        ):
            raise ValidationError(
                f"Una unidad puede tener máximo {self.MAXIMO_CATEGORIAS} categorías."
            )

    def save(self, *args, **kwargs):
        if not self.clasificacion_funcional:
            self.clasificacion_funcional = self.CLASIFICACION_PREDETERMINADA.get(
                self.codigo_base,
                "",
            )
        super().save(*args, **kwargs)

    class Meta:
        db_table = "webcitt_unidad"
        verbose_name = "Unidad"
        verbose_name_plural = "Unidades"
