"""La ficha explicativa de un área: qué es, cómo funciona, qué se hace y con qué.

La página de cada área muestra lo que el área tiene registrado (equipos, software, procesos)
y, con esta ficha, lo que explica la tecnología y lo que el área necesita para trabajar:
equipamiento de referencia por nivel, software con su licencia, documentación, conexiones y
seguridad. El público la ve cuando la unidad la marca como publicada.
"""
import re

from django.db import models
from django.templatetags.static import static


class FichaArea(models.Model):
    espacio = models.OneToOneField('gestion_unidades.EspacioReservable', on_delete=models.CASCADE, related_name='ficha')
    que_es = models.TextField('Qué es', blank=True,
                             help_text='La tecnología o el trabajo del área, para alguien que nunca lo usó.')
    como_funciona = models.TextField('Cómo funciona', blank=True,
                                     help_text='El principio técnico, sin jerga; si usa un término técnico, explíquelo.')
    aplicaciones = models.TextField('Qué se puede hacer', blank=True, help_text='Una aplicación por línea.')
    principio = models.TextField(
        'Cómo funciona, paso a paso', blank=True,
        help_text='Un paso por línea, con el formato «Paso | explicación». La página lo dibuja como diagrama.')
    distribucion = models.TextField(
        'Distribución del área', blank=True,
        help_text='Una zona por línea, con el formato «Zona | qué se hace | equipo; otro equipo». '
                  'La página la dibuja como boceto y resalta los equipos de cada zona.')
    conexiones = models.TextField('Conexiones e infraestructura', blank=True,
                                  help_text='Red, energía, extracción, aire y lo demás que el área necesita. Una por línea.')
    seguridad = models.TextField('Seguridad', blank=True, help_text='Una regla por línea.')
    fuente = models.CharField('Fuente', max_length=200, blank=True,
                              help_text='De dónde sale el contenido, si no es del propio laboratorio.')
    publicada = models.BooleanField('Publicada', default=False,
                                    help_text='Sin marcar, solo la ve quien gestiona la unidad, como borrador.')
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_fichaarea'
        verbose_name = 'Ficha del área'
        verbose_name_plural = 'Fichas de las áreas'

    def __str__(self):
        return f'Ficha de {self.espacio}'

    @staticmethod
    def _lineas(texto):
        return [linea.strip(' -•\t') for linea in texto.splitlines() if linea.strip(' -•\t')]

    @property
    def pasos(self):
        """Los pasos del diagrama «cómo funciona», como (título, explicación)."""
        return [tuple(parte.strip() for parte in (linea.split('|', 1) + [''])[:2]) for linea in self._lineas(self.principio)]

    @property
    def zonas(self):
        """Las zonas del boceto, como diccionarios con su nombre, su uso y sus equipos."""
        zonas = []
        for linea in self._lineas(self.distribucion):
            nombre, uso, equipos = (linea.split('|') + ['', ''])[:3]
            zonas.append({'nombre': nombre.strip(), 'uso': uso.strip(),
                          'equipos': [equipo.strip() for equipo in equipos.split(';') if equipo.strip()]})
        return zonas

    @property
    def lista_aplicaciones(self):
        return self._lineas(self.aplicaciones)

    @property
    def lista_conexiones(self):
        return self._lineas(self.conexiones)

    @property
    def lista_seguridad(self):
        return self._lineas(self.seguridad)


class ElementoFichaArea(models.Model):
    TIPOS = [
        ('equipo', 'Equipo'),
        ('software', 'Software o aplicación'),
        ('insumo', 'Insumo o material'),
        ('documento', 'Documentación'),
        ('imagen', 'Imagen'),
        ('video', 'Video de YouTube'),
    ]
    # Fotos de catálogo que ilustran un equipo de referencia por su tipo, mientras la unidad no sube la suya.
    FOTOS_DE_CATALOGO = (
        (('láser', 'laser'), 'img/catalogo/fablab/equipos/cortadora-laser.png'),
        (('fresadora', 'cnc', 'router'), 'img/catalogo/fablab/equipos/fresadora-cnc.png'),
        (('escáner 3d', 'escaner 3d', 'escáner de mano'), 'img/catalogo/fablab/equipos/escaner-3d.png'),
        (('resina', 'msla', 'sla'), 'img/catalogo/fablab/equipos/impresora-3d-resina.png'),
        (('impresora 3d', 'fdm'), 'img/catalogo/fablab/equipos/impresora-3d-fdm.png'),
    )
    NIVELES = [
        ('basico', 'Básico'),
        ('alta', 'Alta capacidad'),
    ]

    ficha = models.ForeignKey(FichaArea, on_delete=models.CASCADE, related_name='elementos')
    tipo = models.CharField(max_length=10, choices=TIPOS)
    nivel = models.CharField('Nivel', max_length=10, choices=NIVELES, blank=True,
                             help_text='Solo para equipos: básico para el trabajo diario, alta capacidad para lo exigente.')
    nombre = models.CharField(max_length=160)
    icono = models.CharField(max_length=40, blank=True, help_text='Ícono de Font Awesome; ilustra el equipo si no hay foto.')
    foto = models.ImageField(upload_to='unidades/fichas_area/', blank=True,
                             help_text='Foto real del equipo o del área. Si no hay, la página usa la imagen referencial.')
    imagen_estatica = models.CharField(
        'Imagen referencial', max_length=200, blank=True,
        help_text='Ruta de una imagen del portal (por ejemplo, img/generated/...). Se muestra rotulada como referencial.')
    para_que = models.CharField('Para qué sirve', max_length=300, blank=True)
    ejemplo = models.CharField('Ejemplo de modelo o presentación', max_length=200, blank=True,
                               help_text='En equipos, un modelo de ejemplo; en insumos, la presentación.')
    cantidad = models.CharField('Cantidad', max_length=120, blank=True,
                                help_text='En equipos, la cantidad sugerida; en insumos, el consumo de referencia.')
    solo_referencia = models.BooleanField(
        'Dotación propuesta', default=False,
        help_text='Referencia para evaluar una capacidad futura. No crea equipos físicos, existencias ni licencias al sincronizar.')
    especificaciones = models.TextField(blank=True, help_text='Solo para equipos: una por línea, «Característica: valor».')
    consumibles = models.TextField('Insumos que usa', blank=True, help_text='Solo para equipos: uno por línea.')
    cuidados = models.TextField('Cuidados', blank=True, help_text='Solo para equipos: mantenimiento y uso seguro, uno por línea.')
    registrado = models.ForeignKey(
        'recursos.UnidadEquipo', on_delete=models.SET_NULL, null=True, blank=True, related_name='elementos_de_ficha',
        help_text='El equipo del inventario de la unidad, si este elemento ya está registrado.')
    insumo_registrado = models.ForeignKey(
        'recursos.Consumible', on_delete=models.SET_NULL, null=True, blank=True, related_name='elementos_de_ficha',
        help_text='Solo para insumos: el material del inventario de la unidad, con su stock.')
    software_registrado = models.ForeignKey(
        'recursos.SoftwareDisponible', on_delete=models.SET_NULL, null=True, blank=True, related_name='elementos_de_ficha',
        help_text='Solo para software: el programa registrado en la unidad, con sus licencias.')
    licencia = models.CharField(max_length=120, blank=True, help_text='Solo para software.')
    url = models.URLField('Enlace', max_length=500, blank=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'webcitt_elementofichaarea'
        ordering = ('tipo', 'orden', 'id')
        verbose_name = 'Elemento de la ficha'
        verbose_name_plural = 'Equipos, insumos, software, documentación, imágenes y videos de la ficha'

    def __str__(self):
        return self.nombre

    _lineas = staticmethod(FichaArea._lineas)

    @property
    def lista_especificaciones(self):
        return [tuple(parte.strip() for parte in (linea.split(':', 1) + [''])[:2]) for linea in self._lineas(self.especificaciones)]

    @property
    def lista_consumibles(self):
        return self._lineas(self.consumibles)

    @property
    def lista_cuidados(self):
        return self._lineas(self.cuidados)

    @property
    def imagen_url(self):
        """La foto propia; si no, la del equipo registrado, la referencial o la de catálogo de su tipo."""
        if self.foto:
            return self.foto.url
        if self.registrado_id:
            equipo = self.registrado.equipo
            if equipo.imagen:
                return equipo.imagen.url
            if equipo.imagen_catalogo:
                return static(equipo.imagen_catalogo)
        if self.imagen_estatica:
            return static(self.imagen_estatica)
        if self.tipo == 'equipo':
            nombre = self.nombre.lower()
            for palabras, ruta in self.FOTOS_DE_CATALOGO:
                if any(palabra in nombre for palabra in palabras):
                    return static(ruta)
        return ''

    @property
    def es_referencial(self):
        """La imagen no es del área ni del equipo: ilustra su tipo de trabajo."""
        return not self.foto and not (self.registrado_id and (self.registrado.equipo.imagen
                                                              or self.registrado.equipo.imagen_catalogo))

    @property
    def youtube_id(self):
        """El identificador del video, desde cualquier forma de enlace de YouTube."""
        coincidencia = re.search(r'(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})', self.url)
        return coincidencia.group(1) if coincidencia else ''
