import hashlib
import re
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.fields.files import FieldFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify

from apps.directorio_unidades.models.core import Unidad


VISIBILIDADES_CONTENIDO = [
    ('publica', 'Pública'),
    ('restringida', 'Comunidad universitaria'),
    ('interna', 'Solo personal de la unidad'),
]

TIPOS_ADJUNTO = [
    ('microproyecto_django', 'Microproyecto Django (ZIP con SQLite)'),
    ('manual', 'Manual'),
    ('plano', 'Plano'),
    ('ficha_tecnica', 'Ficha técnica'),
    ('hoja_seguridad', 'Hoja de seguridad'),
    ('certificado', 'Certificado'),
    ('norma', 'Norma'),
    ('evidencia', 'Evidencia'),
    ('informe', 'Informe'),
    ('publicacion', 'Publicación'),
    ('dataset', 'Dataset'),
    ('plantilla', 'Plantilla'),
    ('multimedia', 'Multimedia'),
    ('recorrido_360', 'Recorrido 360° (ZIP con index.html)'),
    ('artefacto', 'Artefacto'),
]

FORMATOS_ADJUNTO_PERMITIDOS = {
    '.pdf', '.doc', '.docx', '.odt', '.xls', '.xlsx', '.ods', '.csv', '.tsv',
    '.json', '.xml', '.txt', '.md', '.html', '.htm', '.zip', '.png', '.jpg',
    '.jpeg', '.webp', '.svg', '.mp4', '.webm', '.mov', '.dwg', '.dxf', '.step',
    '.stp', '.iges', '.igs', '.obj', '.stl', '.glb', '.gltf', '.ipynb', '.py',
}
LIMITE_ORDINARIO_ADJUNTO = 200 * 1024 * 1024
# Contenido máximo de un ZIP al extraerlo; el mismo tope que los microproyectos.
ZIP_MAX_DESCOMPRIMIDO = 512 * 1024 * 1024
ZIP_MAX_ARCHIVOS = 20000


def _resumen_archivo(archivo):
    """Conserva archivos del llamador y cierra los que abre para inspeccionar."""
    if not archivo:
        return 0, ''
    cerrar = isinstance(archivo, FieldFile) and archivo.closed
    posicion = None
    try:
        if cerrar:
            archivo.open('rb')
        posicion = archivo.tell() if hasattr(archivo, 'tell') else None
        if hasattr(archivo, 'seek'):
            archivo.seek(0)
        huella = hashlib.sha256()
        total = 0
        bloques = archivo.chunks() if hasattr(archivo, 'chunks') else iter(lambda: archivo.read(1024 * 1024), b'')
        for bloque in bloques:
            huella.update(bloque)
            total += len(bloque)
        return total, huella.hexdigest()
    finally:
        if cerrar:
            archivo.close()
        elif hasattr(archivo, 'seek') and posicion is not None:
            archivo.seek(posicion)


def ruta_adjunto(instancia, nombre_original):
    """Compone el nombre institucional; la persona solo declara el título."""
    extension = Path(nombre_original).suffix.lower()
    contenedor = instancia.codigo_contenedor or 'UPEC'
    titulo = slugify(instancia.nombre)[:70] or 'archivo'
    fecha = instancia.fecha_documento or (
        instancia.fecha_subida.date() if instancia.fecha_subida else timezone.localdate()
    )
    fecha_texto = fecha.isoformat()
    nombre = f'{contenedor}_{instancia.tipo_adjunto}_{titulo}_v{instancia.version}_{fecha_texto}{extension}'
    return f'recursos/adjuntos/{slugify(instancia.unidad.codigo or instancia.unidad.nombre)}/{nombre}'

DEFAULT_MODULES_BY_DEPENDENCIA = {
    'laboratorios': [
        ('informacion-general', 'Información general', 'iconsminds-gears', False),
        ('areas-equipos', 'Áreas y equipos', 'iconsminds-optimization', False),
        ('procesos-productos', 'Procesos y productos', 'iconsminds-gear', False),
        ('docencia-capacitacion', 'Docencia y capacitación', 'iconsminds-library', False),
        ('reservas-servicios', 'Reservas y servicios', 'iconsminds-calendar', True),
        ('investigacion-formativa', 'Investigación formativa y vinculación', 'iconsminds-big-data', False),
    ],
    'observatorios': [
        ('informacion-general', 'Información general', 'iconsminds-gears', False),
        ('datos-indicadores', 'Datos y monitoreo', 'iconsminds-data-center', False),
        ('reportes-publicaciones', 'Reportes y publicaciones', 'iconsminds-file', False),
        ('investigacion-vinculacion', 'Investigación y vinculación', 'iconsminds-big-data', False),
        ('acceso-servicios', 'Acceso y servicios', 'iconsminds-conference', True),
    ],
    'plantas_piloto': [
        ('informacion-general', 'Información general', 'iconsminds-gears', False),
        ('procesos-protocolos', 'Procesos y protocolos', 'iconsminds-gear', False),
        ('equipos-infraestructura', 'Equipos e infraestructura', 'iconsminds-factory', False),
        ('produccion-lotes', 'Producción y lotes', 'iconsminds-box-with-folders', False),
        ('calidad-inocuidad', 'Calidad e inocuidad', 'iconsminds-check', False),
        ('reservas-servicios', 'Reservas y servicios', 'iconsminds-calendar', True),
    ],
    'centro_experimental': [
        ('informacion-general', 'Información general', 'iconsminds-gears', False),
        ('areas-productivas', 'Áreas y sistemas productivos', 'iconsminds-environmental-3', False),
        ('produccion-ensayos', 'Producción y ensayos', 'iconsminds-plant', False),
        ('infraestructura-equipos', 'Infraestructura y equipos', 'iconsminds-factory', False),
        ('investigacion-vinculacion', 'Investigación y vinculación', 'iconsminds-big-data', False),
        ('visitas-servicios', 'Visitas y servicios', 'iconsminds-calendar', True),
    ],
}

RESERVATION_MODULE_BY_DEPENDENCIA = {
    'laboratorios': 'reservas-servicios',
    'observatorios': 'acceso-servicios',
    'plantas_piloto': 'reservas-servicios',
    'centro_experimental': 'visitas-servicios',
}


class ModuloUnidad(models.Model):
    ICON_CHOICES = [
        ('iconsminds-gears', 'Información / configuración'),
        ('iconsminds-library', 'Recursos / biblioteca'),
        ('iconsminds-optimization', 'Tecnología / software'),
        ('iconsminds-conference', 'Gestión / servicios'),
        ('iconsminds-big-data', 'Datos / proyectos'),
        ('iconsminds-communication-tower-2', 'Comunidad / vinculación'),
        ('iconsminds-data-center', 'Indicadores / datos'),
        ('iconsminds-bell', 'Monitoreo / alertas'),
        ('iconsminds-file', 'Documentos / publicaciones'),
        ('iconsminds-gear', 'Procesos'),
        ('iconsminds-factory', 'Infraestructura / planta'),
        ('iconsminds-box-with-folders', 'Producción / lotes'),
        ('iconsminds-check', 'Calidad'),
        ('iconsminds-calendar', 'Reservas / calendario'),
        ('iconsminds-environmental-3', 'Áreas productivas'),
        ('iconsminds-plant', 'Producción agropecuaria'),
        ('iconsminds-folder', 'Carpeta general'),
    ]
    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE,
        related_name='modulos_contenido',
    )
    clave = models.SlugField(
        max_length=80,
        blank=True,
        help_text='Identificador interno. Se completa automáticamente a partir del nombre.',
    )
    nombre = models.CharField(max_length=120)
    icono = models.CharField(
        max_length=80,
        default='iconsminds-folder',
        choices=ICON_CHOICES,
        help_text='Clase CSS del icono, por ejemplo: iconsminds-folder.',
    )
    orden = models.PositiveSmallIntegerField(default=1)
    activo = models.BooleanField(
        default=True,
        help_text='Desactive esta opción para ocultarla sin eliminar sus contenidos.',
    )
    mostrar_herramientas_reserva = models.BooleanField(
        default=False,
        help_text='Incluye accesos a reservas, mis reservas y reglamento de uso.',
    )

    class Meta:
        db_table = 'webcitt_modulounidad'
        ordering = ('orden', 'id')
        unique_together = ('unidad', 'clave')
        verbose_name = 'Módulo de contenido'
        verbose_name_plural = 'Módulos de contenido'

    def save(self, *args, **kwargs):
        if not self.clave:
            base_key = slugify(self.nombre) or 'modulo'
            candidate = base_key
            suffix = 2
            existing = ModuloUnidad.objects.filter(unidad_id=self.unidad_id)
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            while existing.filter(clave=candidate).exists():
                candidate = f'{base_key}-{suffix}'
                suffix += 1
            self.clave = candidate
        reservation_key = RESERVATION_MODULE_BY_DEPENDENCIA.get(
            self.unidad.codigo_base,
            'reservas-servicios',
        )
        self.mostrar_herramientas_reserva = self.clave == reservation_key
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


def create_default_modules(unidad):
    defaults = DEFAULT_MODULES_BY_DEPENDENCIA.get(
        unidad.codigo_base,
        DEFAULT_MODULES_BY_DEPENDENCIA['laboratorios'],
    )
    return [
        ModuloUnidad.objects.create(
            unidad=unidad,
            clave=clave,
            nombre=nombre,
            icono=icono,
            orden=orden,
            mostrar_herramientas_reserva=reservas,
        )
        for orden, (clave, nombre, icono, reservas) in enumerate(defaults, start=1)
    ]


@receiver(post_save, sender=Unidad)
def initialize_project_modules(sender, instance, created, **kwargs):
    if created and not instance.modulos_contenido.exists():
        create_default_modules(instance)

class CarpetaRecurso(models.Model):  # Modelo para representar carpetas
    MODULO_CHOICES = [
        ('informacionGeneral', 'Información General'),
        ('recursos', 'Recursos y Prácticas'),
        ('software', 'Tecnologías y Software'),
        ('reserva', 'Gestión y Reservas'),
        ('proyectos', 'Proyectos'),
        ('colaboracion', 'Formación y Comunidad'),
    ]
    nombre = models.CharField(max_length=255)
    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE,
        related_name='carpetas',
        help_text="Unidad a la que pertenece esta carpeta."
    )
    modulo = models.CharField(max_length=50, choices=MODULO_CHOICES, default='inicio')
    modulo_config = models.ForeignKey(
        ModuloUnidad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='carpetas',
        verbose_name='Módulo de contenido',
        help_text='Módulo configurable en el que aparecerá esta carpeta.',
    )
    # Carpetas que crea el expediente de calidad: se gestionan en el Centro de
    # reportes, no entre los contenidos de la unidad ni en su visor.
    del_expediente = models.BooleanField(default=False, editable=False, db_index=True)
    seccion_planta = models.CharField(
        max_length=3,
        blank=True,
        db_index=True,
        verbose_name='Sección de planta piloto',
        help_text='En plantas piloto integra la carpeta dentro de la sección numerada, sin crear otro menú.',
    )
    ficha = models.ForeignKey(
        'gestion_unidades.FichaContenido',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carpetas_adjuntos',
        help_text='Ficha que contiene esta carpeta. No se combina con una sección.',
    )
    carpeta_padre = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcarpetas',
        verbose_name='Carpeta superior',
        help_text='Opcional. Permite ordenar subcarpetas dentro de una sección.',
    )
    orden = models.PositiveSmallIntegerField(default=0)
    activa = models.BooleanField(
        default=True,
        help_text='Desactive para ocultar la carpeta y todo su contenido sin eliminarlo.',
    )
    visibilidad = models.CharField(
        max_length=20,
        choices=VISIBILIDADES_CONTENIDO,
        default='publica',
    )

    class Meta:
        db_table = 'webcitt_carpetarecurso'
        unique_together = ('nombre', 'unidad')
        ordering = ('orden', 'nombre', 'pk')

    def clean(self):
        super().clean()
        errores = {}
        if self.modulo_config_id and self.unidad_id:
            if self.modulo_config.unidad_id != self.unidad_id:
                errores['modulo_config'] = 'El módulo seleccionado debe pertenecer a la misma unidad.'
        from apps.plantas_piloto.operacion.presentation.secciones_plantas import mapa_de

        mapa = mapa_de(self.unidad) if self.unidad_id else None
        if self.seccion_planta and self.unidad_id:
            if mapa is None:
                errores['seccion_planta'] = 'Las secciones numeradas solo se usan en plantas piloto y laboratorios.'
            elif self.seccion_planta not in mapa.secciones:
                errores['seccion_planta'] = 'Seleccione una sección válida del mapa de esta unidad.'
            elif self.modulo_config_id and self.modulo_config.clave != mapa.modulo_de(self.seccion_planta):
                errores['modulo_config'] = 'El módulo no corresponde a la sección numerada elegida.'
        # En una pestaña común la carpeta va dentro de una sección numerada; en una propia, directo en ella.
        elif mapa is not None and self.modulo_config_id and self.modulo_config.clave in mapa.pestanas:
            if not self.ficha_id:
                errores['seccion_planta'] = 'Seleccione la sección numerada o la ficha que contiene la carpeta.'
        if self.ficha_id:
            if self.unidad_id and self.ficha.unidad_id != self.unidad_id:
                errores['ficha'] = 'La ficha debe pertenecer a la misma unidad.'
            if self.seccion_planta:
                errores['ficha'] = 'Una carpeta pertenece a una ficha o a una sección, no a ambas.'
        if self.carpeta_padre_id:
            if self.pk and self.carpeta_padre_id == self.pk:
                errores['carpeta_padre'] = 'Una carpeta no puede contenerse a sí misma.'
            if self.unidad_id and self.carpeta_padre.unidad_id != self.unidad_id:
                errores['carpeta_padre'] = 'La carpeta superior debe pertenecer a la misma unidad.'
            if self.seccion_planta and self.carpeta_padre.seccion_planta != self.seccion_planta:
                errores['carpeta_padre'] = 'La carpeta superior debe pertenecer a la misma sección.'
            if self.ficha_id != self.carpeta_padre.ficha_id:
                errores['carpeta_padre'] = 'La carpeta superior debe pertenecer a la misma ficha.'
            if self.carpeta_padre.carpeta_padre_id:
                errores['carpeta_padre'] = 'Solo se permiten dos niveles de carpetas dentro del contenedor.'
            ancestro = self.carpeta_padre
            visitados = {self.pk} if self.pk else set()
            while ancestro:
                if ancestro.pk in visitados:
                    errores['carpeta_padre'] = 'La jerarquía de carpetas no puede formar un ciclo.'
                    break
                visitados.add(ancestro.pk)
                ancestro = ancestro.carpeta_padre
        if errores:
            raise ValidationError(errores)

    def __str__(self):
        return self.nombre

class Archivo(models.Model):
    TIPO_ARCHIVO_CHOICES = [
        ('pdf', 'PDF'),
        ('html', 'HTML'),
        ('imagen', 'Imagen'),
        ('video', 'Video'),
        ('otro', 'Otro'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_ARCHIVO_CHOICES)
    archivo = models.FileField(upload_to='recursos/archivos/', blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.archivo and self.url:
            raise ValidationError("Solo puede proporcionar un archivo o una URL, no ambos.")
        if not self.archivo and not self.url:
            raise ValidationError("Debe proporcionar un archivo o una URL.")

    def __str__(self):
        return f"{self.tipo} - {self.archivo.name if self.archivo else self.url}"

    class Meta:
        db_table = 'webcitt_archivo'

DEPENDENCIA_MICROPROYECTO = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*(==[A-Za-z0-9_.+-]+)?')


def validar_dependencias_microproyecto(texto):
    invalidas = [x for x in texto.split() if not DEPENDENCIA_MICROPROYECTO.fullmatch(x)]
    if invalidas:
        raise ValidationError('Use nombre o nombre==versión, separados por espacios, sin URLs ni opciones de pip: '
                              + ', '.join(invalidas))


class Recurso(models.Model):
    nombre = models.CharField(max_length=255)
    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE,
        related_name='recursos',
        help_text="Unidad a la que pertenece este recurso."
    )
    archivo = models.FileField(
        upload_to=ruta_adjunto,
        blank=True,
        null=True,
        help_text='Archivo de cualquier tipo. Un ZIP debe contener index.html y sus recursos.'
    )
    url = models.URLField(
        blank=True,
        help_text='Enlace externo alternativo al archivo. Use solo uno de los dos campos.',
    )
    activo = models.BooleanField(default=True)
    visibilidad = models.CharField(
        max_length=20,
        choices=VISIBILIDADES_CONTENIDO,
        default='publica',
    )
    descargar = models.BooleanField(
        default=False, 
        help_text="Permitir descarga del archivo"
    )
    carpeta = models.ForeignKey(
        CarpetaRecurso,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recursos'
    )
    orden = models.PositiveSmallIntegerField(default=0)
    descripcion = models.TextField(
        blank=False,
        default='',
        help_text='Una frase que permita entender el archivo sin abrirlo.',
    )
    tipo_adjunto = models.CharField(max_length=24, choices=TIPOS_ADJUNTO, default='informe')
    microproyecto_url = models.URLField(blank=True, editable=False)
    microproyecto_hash = models.CharField(max_length=64, blank=True, editable=False)
    navegador_remoto = models.BooleanField(
        'Usar navegador remoto', default=False,
        help_text='Si el sitio prohíbe mostrarse dentro de otras páginas, se abre en un navegador del '
                  'servidor para usuarios con sesión iniciada, con cupo limitado.',
    )
    microproyecto_dependencias = models.CharField(
        'Dependencias adicionales', max_length=500, blank=True, validators=[validar_dependencias_microproyecto],
        help_text='Solo si el paquete omite alguna en requirements.txt. Separadas por espacios, '
                  'por ejemplo: django-unfold==0.91.0',
    )
    ficha = models.ForeignKey(
        'gestion_unidades.FichaContenido',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='adjuntos',
        help_text='Ficha a la que respalda. Si queda vacío, pertenece a la carpeta o a la unidad.',
    )
    nombre_original = models.CharField(max_length=255, blank=True, editable=False)
    formato = models.CharField(max_length=20, blank=True, editable=False)
    tamano_bytes = models.PositiveBigIntegerField(default=0, editable=False)
    hash_sha256 = models.CharField(max_length=64, blank=True, db_index=True, editable=False)
    autor = models.CharField(max_length=180, blank=True)
    fecha_documento = models.DateField(null=True, blank=True)
    fecha_subida = models.DateTimeField(default=timezone.now, editable=False)
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='adjuntos_unidad_subidos',
        editable=False,
    )
    fuente = models.CharField(
        max_length=20,
        choices=(
            ('interna', 'Interna UPEC'), ('proveedor', 'Proveedor'),
            ('norma', 'Norma'), ('publicacion', 'Publicación'), ('externa', 'Externa'),
        ),
        default='interna',
    )
    licencia_uso = models.CharField(
        max_length=20,
        choices=(
            ('libre', 'Libre'), ('interna', 'Uso interno'),
            ('restringida', 'Restringida'), ('permiso_autor', 'Con permiso del autor'),
        ),
        default='interna',
    )
    version = models.PositiveSmallIntegerField(default=1)
    reemplaza_a = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='versiones_nuevas',
    )
    estado = models.CharField(
        max_length=12,
        choices=(('vigente', 'Vigente'), ('obsoleto', 'Obsoleto')),
        default='vigente',
    )
    palabras_clave = models.CharField(max_length=300, blank=True)
    seguridad_verificada = models.BooleanField(
        default=False,
        help_text='Confirma que el archivo pasó la revisión antivirus institucional.',
    )
    autorizacion_tamano = models.BooleanField(
        default=False,
        help_text='Autorización excepcional para superar el límite ordinario de 200 MB.',
    )
    veces_descargado = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        db_table = 'webcitt_recurso'
        ordering = ('orden', 'nombre', 'pk')

    def __str__(self):
        return self.nombre

    def get_url_compartir(self):
        from django.urls import reverse
        return reverse('recurso_unidad_compartir', kwargs={
            'recurso_id': self.pk,
            'nombre_url': slugify(self.nombre) or 'contenido',
        })

    def _proteger_informe_mejora(self, bloquear=False):
        from apps.documentos.models.mejora import InformeMejora

        if self.pk and InformeMejora.objects.filter(recurso_id=self.pk).exists():
            raise ValidationError('Los informes de mejora se gestionan desde el expediente de calidad.')
        if self.reemplaza_a_id:
            consulta = InformeMejora.objects
            if bloquear:
                consulta = consulta.select_for_update()
            anterior = consulta.filter(recurso_id=self.reemplaza_a_id).first()
            if anterior and anterior.remitido_en:
                raise ValidationError('No se puede reemplazar un informe de mejora remitido.')

    def clean(self):
        super().clean()
        self._proteger_informe_mejora()
        errores = {}
        if self.pk and not self.es_microproyecto and type(self).objects.filter(
                pk=self.pk, tipo_adjunto='microproyecto_django').exists():
            errores['tipo_adjunto'] = 'Un microproyecto no puede convertirse en un archivo estático.'
        if self.es_zip:
            from apps.recursos.presentation.microproyectos import contiene_django
            if contiene_django(self.archivo):
                errores['tipo_adjunto'] = 'Este ZIP contiene Django. Seleccione «Microproyecto Django» para no publicarlo como archivos estáticos.'
        # El visor abre el recorrido por su index.html: sin él no hay por dónde entrar.
        if self.tipo_adjunto == 'recorrido_360':
            from apps.recursos.presentation.tipos_adjunto import entrada_360, nombres_del_zip
            if not self.es_zip:
                errores['archivo'] = 'El recorrido 360° se carga como el ZIP que exporta su programa (Pano2VR, krpano, 3DVista…).'
            elif not entrada_360(nombres_del_zip(self.archivo)):
                errores['archivo'] = 'El ZIP del recorrido 360° debe traer index.html en la raíz o dentro de una sola carpeta.'
        if self.microproyecto_dependencias:
            from apps.recursos.presentation.despliegue_microproyectos import validar_dependencias
            try:
                validar_dependencias(self.microproyecto_dependencias)
            except ValidationError as exc:
                errores['microproyecto_dependencias'] = exc.messages
        if self.es_microproyecto:
            if self.descargar:
                errores['descargar'] = 'El paquete Python y su SQLite no se publican para descarga. Use la URL del proyecto.'
            if not self.archivo or not self.archivo.name.lower().endswith('.zip'):
                errores['archivo'] = 'Un microproyecto Django debe cargarse como ZIP.'
            else:
                from apps.recursos.presentation.microproyectos import inspeccionar_paquete
                try:
                    inspeccionar_paquete(self.archivo)
                except ValidationError as exc:
                    errores['archivo'] = exc.messages
        if self.archivo and self.url:
            errores['url'] = 'Use un archivo o un enlace, no ambos.'
        if not self.archivo and not self.url:
            errores['archivo'] = 'Debe cargar un archivo o registrar un enlace.'
        if self.url and self.descargar:
            errores['descargar'] = 'La descarga solo puede habilitarse para archivos alojados en la plataforma.'
        if self.carpeta_id and self.unidad_id and self.carpeta.unidad_id != self.unidad_id:
            errores['carpeta'] = 'La carpeta debe pertenecer a la misma unidad.'
        if self.ficha_id and self.unidad_id and self.ficha.unidad_id != self.unidad_id:
            errores['ficha'] = 'La ficha debe pertenecer a la misma unidad.'
        if self.ficha_id and self.carpeta_id and self.carpeta.ficha_id not in (None, self.ficha_id):
            errores['carpeta'] = 'La carpeta pertenece a otra ficha.'
        if not self.descripcion.strip():
            errores['descripcion'] = 'Describe el contenido y para qué sirve antes de subirlo.'
        if self.activo and self.visibilidad in ('publica', 'restringida') and not self.seguridad_verificada and not self.es_microproyecto:
            errores['seguridad_verificada'] = (
                'La revisión de seguridad es obligatoria antes de publicar o restringir el adjunto.'
            )
        if self.archivo:
            extension = Path(self.archivo.name).suffix.lower()
            if extension not in FORMATOS_ADJUNTO_PERMITIDOS:
                errores['archivo'] = 'El formato no está permitido. Los ejecutables nunca se aceptan.'
            tamano, huella = _resumen_archivo(self.archivo)
            if tamano > LIMITE_ORDINARIO_ADJUNTO and not self.autorizacion_tamano:
                errores['archivo'] = 'El archivo supera 200 MB y necesita autorización.'
            duplicado = (type(self).objects.select_related('unidad', 'carpeta').filter(hash_sha256=huella)
                         .exclude(pk=self.pk).first() if huella else None)
            if duplicado:
                # Dónde está, para encontrarlo sin buscar recurso por recurso.
                ubicacion = ', '.join(filter(None, (
                    f'unidad «{duplicado.unidad.nombre}»' if duplicado.unidad_id else '',
                    f'carpeta «{duplicado.carpeta.nombre}»' if duplicado.carpeta_id else '')))
                errores['archivo'] = (
                    f'El archivo ya existe como «{duplicado.nombre}»{f" ({ubicacion})" if ubicacion else ""}. '
                    'Edite ese recurso o comparta su enlace en lugar de duplicarlo.'
                )
        if errores:
            raise ValidationError(errores)

    @property
    def codigo_contenedor(self):
        if self.ficha_id:
            return self.ficha.codigo
        if self.carpeta_id and self.carpeta.seccion_planta:
            return f'{self.unidad.codigo}-{self.carpeta.seccion_planta.replace(".", "")}'
        return self.unidad.codigo or f'UNI-{self.unidad_id}'

    @property
    def metadatos_completos(self):
        return bool(self.nombre and self.descripcion and self.tipo_adjunto and self.unidad_id)

    @property
    def es_microproyecto(self):
        return self.tipo_adjunto == 'microproyecto_django'

    @property
    def nombre_visualizador(self):
        if self.es_microproyecto:
            return 'microproyecto.html'
        return 'sitio-externo.html' if self.es_sitio_externo else ''

    @property
    def es_sitio_externo(self):
        return bool(self.url and not self.archivo)

    @property
    def es_zip(self):
        return bool(not self.es_microproyecto and self.archivo and self.archivo.name.lower().endswith('.zip'))

    @property
    def directorio_extraido(self):
        if not self.archivo:
            return None
        return Path(settings.MEDIA_ROOT, 'recursos', 'archivos', Path(self.archivo.name).stem)

    @transaction.atomic
    def save(self, *args, conservar_reemplazado=False, **kwargs):
        self._proteger_informe_mejora(bloquear=True)
        if self.es_zip:
            from apps.recursos.presentation.microproyectos import contiene_django
            if contiene_django(self.archivo):
                raise ValidationError('Seleccione el tipo Microproyecto Django para este paquete.')
        if self.pk and not self.es_microproyecto and type(self).objects.filter(
                pk=self.pk, tipo_adjunto='microproyecto_django').exists():
            raise ValidationError('Un microproyecto no puede convertirse en ZIP público. Cree otro recurso para un sitio estático.')
        if self.es_microproyecto and self.archivo:
            from apps.recursos.presentation.microproyectos import inspeccionar_paquete
            inspeccionar_paquete(self.archivo)
        if self.archivo:
            if not self.nombre_original:
                self.nombre_original = Path(self.archivo.name).name
            self.formato = Path(self.archivo.name).suffix.lower().lstrip('.')
            self.tamano_bytes, self.hash_sha256 = _resumen_archivo(self.archivo)
        if (self.reemplaza_a_id and not conservar_reemplazado
                and self.reemplaza_a.estado != 'obsoleto'):
            type(self).objects.filter(pk=self.reemplaza_a_id).update(estado='obsoleto', activo=False)
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.es_zip:
                destino = self.directorio_extraido.resolve()
                destino.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(self.archivo.path, 'r') as zip_ref:
                    miembros = zip_ref.infolist()
                    # Un archivo pequeño puede declarar gigabytes al descomprimirse y llenar el volumen de adjuntos.
                    if (len(miembros) > ZIP_MAX_ARCHIVOS
                            or sum(miembro.file_size for miembro in miembros) > ZIP_MAX_DESCOMPRIMIDO):
                        raise ValidationError({'archivo': 'El ZIP supera el contenido permitido al descomprimirse '
                                                          '(512 MB o 20 000 archivos).'})
                    for miembro in miembros:
                        ruta = (destino / miembro.filename).resolve()
                        if ruta != destino and destino not in ruta.parents:
                            raise ValidationError({'archivo': 'El ZIP contiene una ruta no permitida.'})
                    zip_ref.extractall(destino)

class DespliegueMicroproyecto(models.Model):
    """Solicitud de puesta en marcha; la atiende un servicio sin tráfico web."""
    ESTADOS = [('pendiente', 'En cola'), ('en_curso', 'En curso'), ('completado', 'Completado'), ('error', 'Error')]
    ORIGENES = [('automatico', 'Al guardar el ZIP'), ('manual', 'Botón del administrador'), ('consola', 'Consola')]

    recurso = models.ForeignKey(Recurso, on_delete=models.CASCADE, related_name='despliegues')
    hash_sha256 = models.CharField(max_length=64)
    estado = models.CharField(max_length=12, choices=ESTADOS, default='pendiente', db_index=True)
    origen = models.CharField(max_length=12, choices=ORIGENES)
    solicitado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name='despliegues_microproyecto')
    creado = models.DateTimeField(auto_now_add=True)
    iniciado = models.DateTimeField(null=True, blank=True)
    terminado = models.DateTimeField(null=True, blank=True)
    detalle = models.TextField(blank=True)

    class Meta:
        db_table = 'webcitt_desplieguemicroproyecto'
        ordering = ['-creado', '-pk']
        verbose_name = 'Puesta en marcha de microproyecto'
        verbose_name_plural = 'Puestas en marcha de microproyectos'
        permissions = [('solicitar_despliegue_microproyecto', 'Puede poner en marcha microproyectos Django')]

    def __str__(self):
        return f'{self.recurso} · {self.get_estado_display()}'


class SesionNavegador(models.Model):
    """Navegador remoto bajo demanda de un usuario para un sitio externo."""
    ESTADOS = [('pendiente', 'En cola'), ('iniciando', 'Iniciando'), ('activa', 'Activa'),
               ('terminada', 'Terminada'), ('error', 'Error')]

    recurso = models.ForeignKey(Recurso, on_delete=models.CASCADE, related_name='sesiones_navegador')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sesiones_navegador')
    token = models.CharField(max_length=24, unique=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default='pendiente', db_index=True)
    creada = models.DateTimeField(auto_now_add=True)
    iniciada = models.DateTimeField(null=True, blank=True)
    ultima_actividad = models.DateTimeField()
    expira = models.DateTimeField()
    terminada = models.DateTimeField(null=True, blank=True)
    detalle = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = 'webcitt_sesionnavegador'
        ordering = ['-creada']
        verbose_name = 'Sesión de navegador remoto'
        verbose_name_plural = 'Sesiones de navegador remoto'

    def __str__(self):
        return f'{self.recurso} · {self.usuario} · {self.get_estado_display()}'


class ArchivoRecurso(models.Model):
    TIPO_ARCHIVO_CHOICES = [
        ('pdf', 'PDF'),
        ('html', 'HTML'),
        ('imagen', 'Imagen'),
        ('video', 'Video'),
        ('otro', 'Otro'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_ARCHIVO_CHOICES)
    archivo = models.FileField(upload_to='recursos/archivos/', blank=True, null=True)
    url = models.URLField(blank=True, null=True)  # Nuevo campo para URL
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Validar que solo uno de los campos 'archivo' o 'url' esté presente
        if self.archivo and self.url:
            raise ValidationError("Solo puede proporcionar un archivo o una URL, no ambos.")
        if not self.archivo and not self.url:
            raise ValidationError("Debe proporcionar un archivo o una URL.")

    def __str__(self):
        return f"{self.tipo} - {self.archivo.name if self.archivo else self.url}"

    class Meta:
        db_table = 'webcitt_archivorecurso'


class ReglamentoUnidad(models.Model):
    unidad = models.OneToOneField(
        Unidad,
        on_delete=models.CASCADE,
        related_name='reglamento_publico',
    )
    titulo = models.CharField(max_length=180, default='Reglamento de uso de la unidad')
    subtitulo = models.CharField(
        max_length=255,
        default='Lineamientos para el uso responsable de espacios, equipos y recursos.',
    )
    normas_generales = models.TextField(
        help_text='Escriba una norma por línea.',
    )
    reservas_horarios = models.TextField(
        help_text='Escriba una condición por línea.',
    )
    equipos_materiales = models.TextField(
        help_text='Escriba una indicación por línea.',
    )
    seguridad = models.TextField(
        help_text='Escriba una medida por línea.',
    )
    contacto_texto = models.CharField(
        max_length=255,
        default='Para dudas o emergencias, comunícate con el equipo responsable.',
    )
    contacto_email = models.EmailField(default='laboratorio@upec.edu.ec')
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'webcitt_reglamentounidad'
        verbose_name = 'Reglamento de uso'
        verbose_name_plural = 'Reglamento de uso'

    def __str__(self):
        return f'Reglamento: {self.unidad.nombre}'


# Texto genérico con el que nace cada unidad. El reglamento oficial se redacta en el expediente
# (documento REGLAMENTO-USO) y, al enviarse, reemplaza este texto en la página pública.
REGLAMENTO_GENERICO = {
    'normas_generales': 'Utiliza responsablemente los espacios y recursos.\nMantén el orden y la limpieza.\nCumple las indicaciones del personal responsable.',
    'reservas_horarios': 'Realiza las reservas mediante el sistema institucional.\nRespeta el horario autorizado.\nCancela con anticipación cuando no puedas asistir.',
    'equipos_materiales': 'Verifica el estado antes de utilizar cada recurso.\nReporta daños o funcionamiento irregular.\nEntrega los equipos y materiales en las condiciones recibidas.',
    'seguridad': 'Utiliza los elementos de protección requeridos.\nIdentifica las rutas y elementos de emergencia.\nReporta inmediatamente cualquier incidente.',
}


def create_default_unit_content(unidad):
    ReglamentoUnidad.objects.get_or_create(
        unidad=unidad,
        defaults={
            'titulo': f'Reglamento de uso de {unidad.nombre}',
            **REGLAMENTO_GENERICO,
            'contacto_email': unidad.contacto_email or 'laboratorio@upec.edu.ec',
        },
    )


@receiver(post_save, sender=Unidad)
def initialize_project_public_content(sender, instance, created, **kwargs):
    if created:
        create_default_unit_content(instance)
