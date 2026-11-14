import re

from django.core.exceptions import ValidationError
from django.db import models
from django.templatetags.static import static
from django.utils.html import format_html_join
from apps.recursos.models.medios import medios_publicos, validar_medios_referencia


class CategoriaEquipo(models.Model):
    """Modelo para las categorías de equipos"""
    
    nombre = models.CharField(
        max_length=50,
        unique=True,
        help_text="Nombre de la categoría"
    )
    
    codigo = models.CharField(
        max_length=20,
        unique=True,
        help_text="Código único de la categoría"
    )
    
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción de la categoría"
    )
    
    icono = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Emoji o icono para la categoría"
    )
    
    color = models.CharField(
        max_length=7,
        default='#007bff',
        help_text="Color hex para la categoría (ej: #007bff)"
    )
    
    activa = models.BooleanField(
        default=True,
        help_text="Si la categoría está activa"
    )
    
    orden = models.PositiveIntegerField(
        default=0,
        help_text="Orden de visualización"
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'webcitt_categoriaequipo'
        ordering = ['orden', 'nombre']
        verbose_name = 'Categoría de Equipo'
        verbose_name_plural = 'Categorías de Equipos'
    
    def __str__(self):
        return f"{self.icono} {self.nombre}" if self.icono else self.nombre

    @property
    def color_seguro(self):
        """Solo admite el color hexadecimal esperado dentro de HTML."""
        color = str(self.color or "")
        return color if re.fullmatch(r"#[0-9a-fA-F]{6}", color) else "#007bff"


class FamiliaEquipo(models.Model):
    """El mismo producto en todas las unidades, para ver cuántos hay y dirigir las compras."""
    nombre = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    grupo = models.CharField(max_length=80, blank=True, help_text='Agrupación amplia, por ejemplo «Realidad extendida».')
    icono = models.CharField(max_length=40, blank=True, help_text='Ícono de Font Awesome, por ejemplo fas fa-vr-cardboard.')
    descripcion = models.TextField(blank=True)
    # Referencia de la familia, mientras el modelo no registre los suyos (cargar_componentes_familias).
    componentes = models.JSONField(
        default=list, blank=True,
        help_text='Lista de {tipo: incluido|complementario|repuesto, cantidad, nombre, uso}.')
    modos_uso = models.JSONField(
        'Modos de uso', default=list, blank=True,
        help_text='Lista de {nombre, icono, descripcion, aplicaciones: [...], requisitos: [...]}.')
    sistema = models.CharField('Sistema o firmware', max_length=300, blank=True,
                               help_text='Con qué sistema, firmware o software de control funciona y cómo se actualiza.')

    class Meta:
        db_table = 'webcitt_familiaequipo'
        ordering = ('grupo', 'nombre')
        verbose_name = 'Familia de equipo'
        verbose_name_plural = 'Familias de equipo'

    def __str__(self):
        return self.nombre


class EquiposServicios(models.Model):
    """Modelo técnico de un equipo de la unidad.

    Un equipo **principal** se reserva y se opera por sí mismo: la impresora
    3D, el termociclador, la pasteurizadora. Un equipo **auxiliar** acompaña a
    uno o varios principales y no se reserva aparte: el secador de filamento,
    la balanza, la bomba de vacío. El asistente ofrece los principales y
    muestra los auxiliares dentro de la tarjeta del principal al que apoyan.
    """

    ROLES = [
        ('principal', 'Equipo principal'),
        ('auxiliar', 'Equipo auxiliar'),
    ]
    
    ESTADO_CHOICES = [
        ('disponible', 'Disponible'),
        ('en_uso', 'En Uso'),
        ('mantenimiento', 'En Mantenimiento'),
        ('no_disponible', 'No Disponible'),
    ]
    FAMILIA_TECNOLOGICA_CHOICES = [
        ('tratamiento_termico', 'Tratamiento térmico'),
        ('fermentacion', 'Fermentación'),
        ('deshidratacion', 'Deshidratación'),
        ('congelacion', 'Congelación'),
        ('extraccion', 'Extracción'),
        ('envasado_vacio_map', 'Envasado al vacío / MAP'),
        ('destilacion', 'Destilación'),
    ]
    MODOS_OPERACION = [
        ('continuo', 'Continuo'),
        ('lote', 'Por lote'),
        ('discreto', 'Discreto'),
    ]
    CRITICIDADES = [
        ('A', 'A · Crítico para el proceso'),
        ('B', 'B · Importante'),
        ('C', 'C · Apoyo'),
    ]
    
    # Información básica del equipo
    codigo = models.CharField(
        max_length=20, 
        unique=True,
        help_text="Código único del equipo"
    )
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre del equipo"
    )
    descripcion = models.TextField(
        blank=True, 
        null=True,
        help_text="Descripción detallada del equipo"
    )
    
    # RELACIÓN MANY-TO-MANY CON CATEGORÍAS
    categorias = models.ManyToManyField(
        CategoriaEquipo, db_table='webcitt_equiposservicios_categorias',
        blank=True,
        related_name='equipos',
        help_text="Categorías a las que pertenece el equipo"
    )
    
    # Documentación y recursos
    vida_util_referencia_anios = models.PositiveSmallIntegerField(
        'Vida útil de referencia (años)',
        default=0,
        help_text='Años que la institución espera de este tipo de equipo. Cada activo puede ajustarla.',
    )

    vida_util_horas = models.PositiveIntegerField(
        'Vida útil por uso (horas)',
        default=0,
        help_text='Horas de operación que agotan el equipo. 0: la vida útil solo se mide por tiempo.',
    )

    manual_operacion = models.FileField(
        upload_to='manuales_equipos/',
        blank=True,
        null=True,
        help_text="Manual de operación del equipo"
    )
    imagen = models.ImageField(
        upload_to='imagenes_equipos/',
        blank=True,
        null=True,
        help_text="Imagen del equipo"
    )
    imagen_catalogo = models.CharField(
        'Ruta de imagen pública',
        max_length=255,
        blank=True,
        help_text='Ruta relativa en archivos estáticos, por ejemplo img/catalogo/equipos/impresora.png.',
    )
    credito_imagen = models.CharField(
        'Crédito de la imagen',
        max_length=300,
        blank=True,
        help_text='Autor y licencia de la imagen de catálogo cuando no es propia de la unidad.',
    )
    medios_referencia = models.JSONField(
        default=dict, blank=True, validators=[validar_medios_referencia],
        help_text='Procedencia, documentación y medios del modelo; la identificación física de cada activo se verifica aparte.',
    )
    fuente_imagen = models.URLField(
        'Fuente de la imagen',
        max_length=500,
        blank=True,
        help_text='Página de origen de la imagen de catálogo (por ejemplo, su archivo en Wikimedia Commons).',
    )
    icono = models.CharField(
        'Ícono',
        max_length=40,
        blank=True,
        help_text='Ícono de Font Awesome (por ejemplo, fas fa-cube) que identifica el equipo en los menús.',
    )
    familia = models.ForeignKey(
        FamiliaEquipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tipos',
        help_text='La familia de producto: agrupa el mismo equipo en todas las unidades para dirigir las compras.',
    )
    caracteristicas_publicas = models.TextField(
        'Características públicas',
        blank=True,
        help_text='Capacidades y especificaciones que ayudan al usuario a elegir el equipo.',
    )
    especificaciones = models.JSONField(
        default=dict, blank=True,
        help_text='Especificaciones de la plantilla de su grupo de producto, por ejemplo {"Procesador": "Intel Xeon…"}.',
    )
    uso_publico = models.TextField(
        '¿Para qué se utiliza?',
        blank=True,
        help_text='Aplicaciones y resultados que el usuario puede obtener con este equipo.',
    )
    instrucciones_publicas = models.TextField(
        'Cómo funciona y cómo prepararse',
        blank=True,
        help_text='Orientación pública previa a la reserva; no sustituye la inducción de seguridad.',
    )
    
    # DOCUMENTACIÓN ADICIONAL
    ficha_tecnica = models.FileField(
        upload_to='fichas_tecnicas/',
        blank=True,
        null=True,
        help_text="Archivo PDF con la ficha técnica del equipo"
    )
    
    video_montaje_cuidados = models.FileField(
        upload_to='videos_equipos/',
        blank=True,
        null=True,
        help_text="Video de montaje y cuidados del equipo (MP4, AVI, MOV)"
    )
    
    explicacion_drivers = models.FileField(
        upload_to='drivers_explicaciones/',
        blank=True,
        null=True,
        help_text="Archivo HTML con explicación de drivers y software necesario"
    )
    
    # Información técnica
    marca = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Marca del equipo"
    )
    modelo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Modelo del equipo"
    )
    fecha_adquisicion = models.DateField(
        blank=True,
        null=True,
        help_text="Fecha de adquisición del equipo"
    )

    # Ficha de levantamiento técnico de Plantas Piloto. Los valores nacen
    # vacíos: una ausencia es un bloqueo visible, nunca un dato estimado que
    # parezca medido por la UPEC. Para validar la planta se pueden cargar
    # valores de referencia, siempre marcados como tales hasta el levantamiento.
    ORIGENES_DATOS_TECNICOS = [
        ('', 'Sin levantamiento'),
        ('referencia', 'Valores de referencia, por verificar en planta'),
        ('medido', 'Levantamiento validado en planta'),
    ]
    origen_datos_tecnicos = models.CharField(
        'Origen de los datos técnicos',
        max_length=12,
        choices=ORIGENES_DATOS_TECNICOS,
        blank=True,
        default='',
        help_text='Al registrar el levantamiento real, márcalo como validado: la carga de '
                  'referencia ya no vuelve a tocar este equipo.',
    )
    capacidad_nominal = models.DecimalField(
        max_digits=12, decimal_places=3, null=True, blank=True,
        help_text='Capacidad declarada por el fabricante; no se usa sola para planificar.',
    )
    unidad_capacidad = models.CharField(
        'Unidad de capacidad', max_length=30, blank=True,
        help_text='Ejemplos: kg/h, L/lote, unidades/min.',
    )
    capacidad_util_min = models.DecimalField(
        'Carga útil mínima', max_digits=12, decimal_places=3, null=True, blank=True,
    )
    capacidad_util_max = models.DecimalField(
        'Carga útil máxima', max_digits=12, decimal_places=3, null=True, blank=True,
    )
    modo_operacion = models.CharField(
        'Modo de operación', max_length=12, choices=MODOS_OPERACION, blank=True,
    )
    tiempo_setup = models.DecimalField(
        'Tiempo de preparación (min)', max_digits=10, decimal_places=2, null=True, blank=True,
    )
    tiempo_limpieza = models.DecimalField(
        'Tiempo de limpieza (min)', max_digits=10, decimal_places=2, null=True, blank=True,
    )
    potencia_kw = models.DecimalField(
        'Potencia (kW)', max_digits=10, decimal_places=3, null=True, blank=True,
    )
    potencia_hp = models.DecimalField(
        'Potencia (HP)', max_digits=10, decimal_places=3, null=True, blank=True,
    )
    voltaje = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    fases = models.PositiveSmallIntegerField(null=True, blank=True)
    frecuencia = models.DecimalField(
        'Frecuencia (Hz)', max_digits=8, decimal_places=2, null=True, blank=True,
    )
    corriente_nominal = models.DecimalField(
        'Corriente nominal (A)', max_digits=10, decimal_places=2, null=True, blank=True,
    )
    grado_proteccion = models.CharField(
        max_length=20, blank=True, help_text='Grado IP u otra clasificación declarada por el fabricante.',
    )
    consumo_vapor = models.DecimalField(
        'Consumo de vapor (kg/h)', max_digits=12, decimal_places=3, null=True, blank=True,
    )
    consumo_agua = models.DecimalField(
        'Consumo de agua (L/ciclo)', max_digits=12, decimal_places=3, null=True, blank=True,
    )
    consumo_aire = models.DecimalField(
        'Consumo de aire (m³/h)', max_digits=12, decimal_places=3, null=True, blank=True,
    )
    largo_mm = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ancho_mm = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    alto_mm = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    peso_kg = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    lados_de_acceso = models.CharField(
        max_length=120, blank=True,
        help_text='Lados que deben quedar libres para operar, limpiar y mantener el equipo.',
    )
    coordenada_x = models.DecimalField(
        max_digits=12, decimal_places=3, null=True, blank=True,
        help_text='Coordenada X del levantamiento de planta; sin ella no se publica el recorrido.',
    )
    coordenada_y = models.DecimalField(
        max_digits=12, decimal_places=3, null=True, blank=True,
        help_text='Coordenada Y del levantamiento de planta; sin ella no se publica el recorrido.',
    )
    posicion_operario_x = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    posicion_operario_y = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    mtbf = models.DecimalField(
        'MTBF (h)', max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Tiempo medio entre fallas validado con historial de mantenimiento.',
    )
    mttr = models.DecimalField(
        'MTTR (h)', max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Tiempo medio de reparación validado con historial de mantenimiento.',
    )
    criticidad = models.CharField(max_length=1, choices=CRITICIDADES, blank=True)
    fecha_ultima_calibracion = models.DateField(null=True, blank=True)
    proxima_calibracion = models.DateField(null=True, blank=True)
    es_compartido = models.BooleanField(default=False)
    plantas_con_acceso = models.ManyToManyField(
        'directorio_unidades.Unidad', db_table='webcitt_equiposservicios_plantas_con_acceso', blank=True, related_name='equipos_con_acceso',
        limit_choices_to={'dependencia': 'plantas_piloto'},
        help_text='Plantas autorizadas a usar este equipo cuando es compartido.',
    )
    
    # Estado del equipo
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='disponible',
        help_text="Estado actual del equipo"
    )
    familia_tecnologica = models.CharField(
        'Familia tecnológica',
        max_length=30,
        choices=FAMILIA_TECNOLOGICA_CHOICES,
        blank=True,
        db_index=True,
        help_text='Tecnología principal usada para filtrar las capacidades de plantas piloto.',
    )
    
    # Software y categorización
    software = models.TextField(
        blank=True,
        null=True,
        help_text="Software requerido o incluido con el equipo"
    )
    admite_software_adicional = models.BooleanField(
        default=False,
        help_text=(
            'El equipo admite instalar otros programas (por ejemplo, una '
            'computadora o estación de trabajo). Al reservarlo, el asistente '
            'pregunta si se necesita instalar software adicional.'
        ),
    )
    cantidad = models.PositiveIntegerField(
        default=1,
        help_text="Cantidad de unidades disponibles"
    )
    
    rol = models.CharField(
        'Rol en la unidad',
        max_length=10,
        choices=ROLES,
        default='principal',
        db_index=True,
        help_text=(
            'Principal: se reserva y se opera por sí mismo. Auxiliar: acompaña '
            'a un equipo principal y no se reserva aparte.'
        ),
    )
    apoya_a = models.ManyToManyField(
        'self', db_table='webcitt_equiposservicios_apoya_a',
        symmetrical=False,
        blank=True,
        related_name='auxiliares',
        verbose_name='Equipos principales a los que apoya',
        help_text='Solo para equipos auxiliares: los principales junto a los que se usa.',
    )

    # Accesorios que llegan con el equipo (lista de textos).
    accesorios_incluidos = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de accesorios incluidos con el equipo (formato JSON)"
    )
    
    accesorios_opcionales = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de accesorios opcionales disponibles para el equipo (formato JSON)"
    )
    modos_uso = models.JSONField(
        'Modos de uso', default=list, blank=True,
        help_text=('Cómo funciona este modelo (autónomo, conectado a una PC…): lista de {nombre, icono, descripcion, '
                   'aplicaciones: [...], requisitos: [...]}. Vacío: se muestran los de su familia.'))
    repuestos = models.JSONField(
        default=list, blank=True,
        help_text='Lo que se cambia o se gasta con el uso, como los accesorios ({nombre, uso, cantidad}). Vacío: los de su familia.')
    
    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'webcitt_equiposservicios'
        ordering = ['nombre']
        verbose_name = 'Equipo/Servicio'
        verbose_name_plural = 'Equipos/Servicios'
        
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @property
    def es_auxiliar(self):
        return self.rol == "auxiliar"

    @property
    def imagen_publica_url(self):
        """Reutiliza exactamente la fotografía mostrada en el catálogo de reservas."""
        if self.imagen:
            try:
                return self.imagen.url
            except ValueError:
                pass
        if self.medios_publicos.get('medios_por_revisar'):
            return ''
        if self.imagen_catalogo:
            return static(self.imagen_catalogo)
        # Sin foto, vacío: las pantallas muestran el ícono del equipo, nunca la foto de otro por una palabra del nombre.
        return ''

    @property
    def medios_publicos(self):
        return medios_publicos(self.medios_referencia)
    
    def save(self, *args, **kwargs):
        anterior = (EquiposServicios.objects.filter(pk=self.pk).values_list('codigo', flat=True).first()
                    if self.pk else None)
        super().save(*args, **kwargs)
        # El código anterior de la ficha técnica sigue llevando al modelo (cargadores, documentos impresos).
        if anterior and anterior != self.codigo:
            AliasCodigoEquipoServicio.objects.get_or_create(codigo=anterior, defaults={'modelo': self})

    def clean(self):
        # Validar que el código sea único
        if EquiposServicios.objects.filter(codigo=self.codigo).exclude(pk=self.pk).exists():
            raise ValidationError("Ya existe un equipo con este código.")
        if AliasCodigoEquipoServicio.objects.filter(codigo=self.codigo).exclude(modelo_id=self.pk).exists():
            raise ValidationError({'codigo': 'Ese código perteneció a otro modelo; elige uno distinto.'})
        
        # Validar formato de ficha técnica (solo PDF)
        if self.ficha_tecnica:
            if not self.ficha_tecnica.name.lower().endswith('.pdf'):
                raise ValidationError("La ficha técnica debe ser un archivo PDF.")
        
        # Validar formato de video
        if self.video_montaje_cuidados:
            formatos_validos = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
            if not any(self.video_montaje_cuidados.name.lower().endswith(fmt) for fmt in formatos_validos):
                raise ValidationError("El video debe ser formato MP4, AVI, MOV, MKV o WebM.")
        
        # Validar formato de explicación de drivers (solo HTML)
        if self.explicacion_drivers:
            if not self.explicacion_drivers.name.lower().endswith('.html'):
                raise ValidationError("La explicación de drivers debe ser un archivo HTML.")
        if (
            self.capacidad_util_min is not None
            and self.capacidad_util_max is not None
            and self.capacidad_util_min > self.capacidad_util_max
        ):
            raise ValidationError({'capacidad_util_max': 'La carga útil máxima no puede ser menor que la mínima.'})
        if (
            self.fecha_ultima_calibracion
            and self.proxima_calibracion
            and self.proxima_calibracion <= self.fecha_ultima_calibracion
        ):
            raise ValidationError({'proxima_calibracion': 'La próxima calibración debe ser posterior a la última.'})

    @property
    def campos_criticos_vacios(self):
        """Datos cuya ausencia bloquea cálculos o diagramas del aula."""
        campos = (
            ('capacidad_util_min', 'Carga útil mínima', 'capacidad'),
            ('capacidad_util_max', 'Carga útil máxima', 'capacidad'),
            ('modo_operacion', 'Modo de operación', 'capacidad'),
            ('tiempo_setup', 'Tiempo de preparación', 'capacidad'),
            ('tiempo_limpieza', 'Tiempo de limpieza', 'capacidad'),
            ('coordenada_x', 'Coordenada X', 'recorrido'),
            ('coordenada_y', 'Coordenada Y', 'recorrido'),
            ('mtbf', 'MTBF', 'simulación de fallas'),
            ('mttr', 'MTTR', 'simulación de fallas'),
        )
        return [
            {'campo': campo, 'nombre': nombre, 'bloquea': bloquea}
            for campo, nombre, bloquea in campos
            if getattr(self, campo) in (None, '')
        ]

    @property
    def completitud_tecnica(self):
        """Cobertura de la ficha de levantamiento, sin convertir ausencias en ceros."""
        nombres = (
            'capacidad_nominal', 'unidad_capacidad', 'capacidad_util_min', 'capacidad_util_max',
            'modo_operacion', 'tiempo_setup', 'tiempo_limpieza', 'potencia_kw', 'potencia_hp',
            'voltaje', 'fases', 'frecuencia', 'corriente_nominal', 'grado_proteccion',
            'consumo_vapor', 'consumo_agua', 'consumo_aire', 'largo_mm', 'ancho_mm', 'alto_mm',
            'peso_kg', 'lados_de_acceso', 'coordenada_x', 'coordenada_y',
            'posicion_operario_x', 'posicion_operario_y', 'mtbf', 'mttr', 'criticidad',
            'fecha_ultima_calibracion', 'proxima_calibracion',
        )
        completos = sum(getattr(self, nombre) not in (None, '') for nombre in nombres)
        total = len(nombres)
        # La condición de compartido está definida incluso cuando es falsa; la
        # lista de plantas solo se exige si el equipo sí se comparte.
        total += 1
        completos += int(not self.es_compartido or (self.pk and self.plantas_con_acceso.exists()))
        return round(completos * 100 / total)
    
    @property
    def disponible(self):
        """Retorna True si el equipo está disponible para reserva"""
        return self.estado == 'disponible' and self.cantidad > 0
    
    @property
    def porcentaje_documentacion(self):
        """Retorna el porcentaje de documentación disponible"""
        documentos = [
            self.manual_operacion,
            self.ficha_tecnica,
            self.video_montaje_cuidados,
            self.explicacion_drivers,
            self.imagen
        ]
        disponibles = sum(1 for doc in documentos if doc)
        return round((disponibles / len(documentos)) * 100)
    
    @property
    def categorias_html(self):
        """Retorna las categorías como badges HTML"""
        return format_html_join(
            "",
            (
                '<span class="badge" style="background-color: {}; color: white; '
                'margin-right: 5px;">{}{}</span>'
            ),
            (
                (
                    categoria.color_seguro,
                    f"{categoria.icono} " if categoria.icono else "",
                    categoria.nombre,
                )
                for categoria in self.categorias.all()
            ),
        )
    
    # Métodos relacionados con unidades individuales
    @property
    def unidades_disponibles(self):
        """Retorna el número de unidades disponibles"""
        return self.unidades.filter(estado_unidad='disponible').count()

    @property
    def unidades_en_uso(self):
        """Retorna el número de unidades en uso"""
        return self.unidades.filter(estado_unidad='en_uso').count()

    @property
    def unidades_mantenimiento(self):
        """Retorna el número de unidades en mantenimiento"""
        return self.unidades.filter(estado_unidad='mantenimiento').count()

    @property
    def porcentaje_disponibilidad(self):
        """Retorna el porcentaje de unidades disponibles"""
        if self.cantidad == 0:
            return 0
        return round((self.unidades_disponibles / self.cantidad) * 100)

    # MÉTODOS PARA DISPONIBILIDAD DINÁMICA BASADA EN RESERVAS
    
    # ✅ NUEVOS MÉTODOS PARA MANEJAR ACCESORIOS
    
    @staticmethod
    def _accesorios_crudos(valor):
        """La lista guardada tal cual: textos sueltos o {"nombre", "uso"} (cómo se usa cada accesorio)."""
        import json

        if isinstance(valor, str):
            try:
                valor = json.loads(valor or '[]')
            except (json.JSONDecodeError, TypeError):
                return []
        return valor if isinstance(valor, list) else []

    @staticmethod
    def _nombres_de_accesorios(lista):
        return [str(item.get('nombre') or '') if isinstance(item, dict) else str(item) for item in lista
                if (item.get('nombre') if isinstance(item, dict) else item)]

    def get_accesorios_incluidos_crudos(self):
        return self._accesorios_crudos(self.accesorios_incluidos)

    def get_accesorios_opcionales_crudos(self):
        return self._accesorios_crudos(self.accesorios_opcionales)

    def get_accesorios_incluidos_list(self):
        """Los nombres de los accesorios incluidos (el uso de cada uno está en la lista cruda)."""
        return self._nombres_de_accesorios(self.get_accesorios_incluidos_crudos())

    def get_accesorios_opcionales_list(self):
        """Los nombres de los accesorios opcionales."""
        return self._nombres_de_accesorios(self.get_accesorios_opcionales_crudos())

    def get_accesorios_incluidos_display(self):
        """Retorna los accesorios incluidos como texto legible"""
        accesorios = self.get_accesorios_incluidos_list()
        if not accesorios:
            return "Ningún accesorio incluido"
        
        if len(accesorios) <= 3:
            return ", ".join(accesorios)
        else:
            return f"{', '.join(accesorios[:3])} y {len(accesorios)-3} más"
    
    def get_accesorios_opcionales_display(self):
        """Retorna los accesorios opcionales como texto legible"""
        accesorios = self.get_accesorios_opcionales_list()
        if not accesorios:
            return "No hay accesorios opcionales"
        
        if len(accesorios) <= 3:
            return ", ".join(accesorios)
        else:
            return f"{', '.join(accesorios[:3])} y {len(accesorios)-3} más"
    
    def get_accesorios_resumen_readonly(self):
        """Genera un resumen de los accesorios para mostrar en el admin"""
        incluidos = self.get_accesorios_incluidos_list()
        opcionales = self.get_accesorios_opcionales_list()
        
        if not incluidos and not opcionales:
            return "No hay accesorios registrados"
            
        partes = []
        if incluidos:
            partes.append(f"Incluidos ({len(incluidos)}): {', '.join(incluidos[:3])}")
            if len(incluidos) > 3:
                partes.append(f"y {len(incluidos)-3} más")
                
        if opcionales:
            if partes:
                partes.append(" | ")
            partes.append(f"Opcionales ({len(opcionales)}): {', '.join(opcionales[:3])}")
            if len(opcionales) > 3:
                partes.append(f"y {len(opcionales)-3} más")
                
        return " ".join(partes)

    def get_accesorios_count_display(self):
        """Retorna el conteo de accesorios para mostrar en el admin"""
        incluidos = len(self.get_accesorios_incluidos_list())
        opcionales = len(self.get_accesorios_opcionales_list())
        return f"{incluidos} inc. + {opcionales} opc."


class AliasCodigoEquipoServicio(models.Model):
    """Código anterior de un modelo (ficha técnica), conservado al estandarizar los códigos."""

    codigo = models.CharField(max_length=20, unique=True)
    modelo = models.ForeignKey(EquiposServicios, on_delete=models.CASCADE, related_name='codigos_anteriores')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_aliascodigoequiposervicio'
        ordering = ('codigo',)
        verbose_name = 'Código anterior de modelo'
        verbose_name_plural = 'Códigos anteriores de modelos'

    def __str__(self):
        return f'{self.codigo} → {self.modelo.codigo}'


class FotoEquipo(models.Model):
    """Una foto del equipo, de un accesorio o de un detalle de uso, para la galería de su ficha técnica."""

    TIPOS = [('equipo', 'Equipo'), ('accesorio', 'Accesorio'), ('detalle', 'Detalle'), ('uso', 'En uso')]

    equipo = models.ForeignKey(EquiposServicios, on_delete=models.CASCADE, related_name='fotos')
    imagen = models.ImageField(upload_to='equipos/galeria/', blank=True)
    imagen_catalogo = models.CharField(max_length=300, blank=True, help_text='Ruta estática de una foto de catálogo.')
    titulo = models.CharField(max_length=160, blank=True)
    tipo = models.CharField(max_length=12, choices=TIPOS, default='equipo')
    credito = models.CharField(max_length=300, blank=True)
    fuente = models.URLField(max_length=500, blank=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'webcitt_fotoequipo'
        ordering = ('orden', 'pk')
        verbose_name = 'Foto del equipo'
        verbose_name_plural = 'Fotos del equipo'

    def __str__(self):
        return self.titulo or f'Foto de {self.equipo.nombre}'

    @property
    def url(self):
        if self.imagen:
            try:
                return self.imagen.url
            except ValueError:
                pass
        return static(self.imagen_catalogo) if self.imagen_catalogo else ''


class VideoEquipo(models.Model):
    """Un video de manejo (uso, operación o mantenimiento), del modelo o de toda su familia de producto."""

    equipo = models.ForeignKey(EquiposServicios, on_delete=models.CASCADE, null=True, blank=True, related_name='videos')
    familia = models.ForeignKey(FamiliaEquipo, on_delete=models.CASCADE, null=True, blank=True, related_name='videos')
    url = models.URLField(max_length=300, help_text='Dirección del video en YouTube.')
    titulo = models.CharField(max_length=200)
    canal = models.CharField(max_length=160, blank=True)
    idioma = models.CharField(max_length=5, default='es')
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'webcitt_videoequipo'
        ordering = ('orden', 'pk')
        verbose_name = 'Video de manejo'
        verbose_name_plural = 'Videos de manejo'

    def __str__(self):
        return self.titulo

    @property
    def youtube_id(self):
        from apps.recursos.models.identificadores import youtube_id

        return youtube_id(self.url)

    def clean(self):
        if bool(self.equipo_id) == bool(self.familia_id):
            raise ValidationError('El video es de un modelo o de una familia (uno de los dos).')
        if not self.youtube_id:
            raise ValidationError({'url': 'Usa la dirección de un video de YouTube.'})


class PiezaEquipo(models.Model):
    """Las partes de un equipo: lo que lo compone, lo que trae y lo que lo protege.

    No son insumos. Un insumo se consume en el trabajo (filamento, resina,
    reactivo) y no cambia el funcionamiento del equipo; una pieza sí: la
    boquilla, el extrusor, la cama o un sensor deciden si el equipo opera y
    con qué calidad. Registrarlas permite saber con qué repuestos cuenta la
    unidad y qué se le ha cambiado a cada activo.
    """

    CLASES = [
        ('componente', 'Componente: parte del equipo que decide su funcionamiento'),
        ('accesorio', 'Accesorio: viene con el equipo y se usa para operarlo'),
        ('proteccion', 'Protección eléctrica o de seguridad'),
        ('herramienta', 'Herramienta o llave de servicio'),
    ]

    equipo = models.ForeignKey(
        EquiposServicios,
        on_delete=models.CASCADE,
        related_name='piezas',
    )
    nombre = models.CharField(max_length=160)
    clase = models.CharField(max_length=12, choices=CLASES, default='componente')
    descripcion = models.CharField(max_length=250, blank=True)
    cantidad = models.PositiveSmallIntegerField(default=1, help_text='Cuántas lleva el equipo.')
    critica = models.BooleanField(
        'Pieza crítica',
        default=False,
        help_text='Sin ella el equipo no opera: conviene tener repuesto.',
    )
    vida_util_horas = models.PositiveIntegerField(
        'Vida útil de la pieza (horas)',
        default=0,
        help_text='Horas de operación tras las que suele reemplazarse. 0: sin desgaste previsto.',
    )
    repuesto_disponible = models.BooleanField(
        'Hay repuesto en la unidad',
        default=False,
    )
    recomendacion = models.CharField(
        max_length=250,
        blank=True,
        help_text='Cuidado o buena práctica que alarga su vida.',
    )
    orden = models.PositiveSmallIntegerField(default=100)

    class Meta:
        db_table = 'webcitt_piezaequipo'
        ordering = ['equipo', 'clase', 'orden', 'nombre']
        verbose_name = 'Pieza o accesorio del equipo'
        verbose_name_plural = 'Piezas y accesorios de los equipos'
        constraints = [
            models.UniqueConstraint(fields=['equipo', 'nombre'], name='pieza_unica_por_equipo'),
        ]

    def __str__(self):
        return f'{self.nombre} · {self.equipo.codigo}'
