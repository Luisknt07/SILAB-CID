"""Repositorio gobernado y contratos de artefactos externos."""

import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.recursos.models.recursos import Recurso, VISIBILIDADES_CONTENIDO


PATRON_CODIGO_ARTEFACTO = re.compile(r'^[A-Z]{3}-SIM-[A-Z0-9]+(?:-[A-Z0-9]+)*$')


class Adjunto(Recurso):
    """Nombre de dominio del recurso documental gobernado en el paso 7."""

    class Meta:
        db_table = 'webcitt_recurso'
        proxy = True
        verbose_name = 'Adjunto gobernado'
        verbose_name_plural = 'Adjuntos gobernados'


class ArtefactoExterno(models.Model):
    TIPOS = (
        ('eventos_discretos', 'Eventos discretos'),
        ('dinamico_control', 'Dinámica y control'),
        ('flowsheet', 'Flowsheet'),
        ('hoja_calculo', 'Hoja de cálculo'),
        ('notebook', 'Notebook'),
        ('xr', 'Experiencia XR'),
        ('cad', 'Modelo CAD'),
        ('dataset', 'Dataset ejecutable'),
        ('aplicacion', 'Aplicación'),
        ('otro', 'Otro'),
    )
    NIVELES = (
        (1, '1 · Integrado'),
        (2, '2 · Conectado'),
        (3, '3 · Depositado'),
    )
    FORMATOS = (('json', 'JSON'), ('csv', 'CSV'), ('xlsx', 'XLSX'))
    ESTADOS_VALIDACION = (
        ('sin_validar', 'Sin validar'),
        ('datos', 'Validado contra datos'),
        ('analitica', 'Validado analíticamente'),
        ('experto', 'Validado por experto'),
    )
    ESTADOS = (
        ('borrador', 'Borrador'),
        ('en_revision', 'En revisión'),
        ('publicado', 'Publicado'),
        ('archivado', 'Archivado'),
    )

    codigo = models.CharField(max_length=90, unique=True)
    nombre = models.CharField(max_length=220)
    descripcion = models.TextField()
    tipo = models.CharField(max_length=24, choices=TIPOS)
    nivel_integracion = models.PositiveSmallIntegerField(choices=NIVELES, default=3)
    unidad = models.ForeignKey('directorio_unidades.Unidad', on_delete=models.CASCADE, related_name='artefactos_externos')
    familia = models.ForeignKey(
        'plantas_operacion.FamiliaProducto', on_delete=models.PROTECT, null=True, blank=True,
        related_name='artefactos_externos',
    )
    receta = models.ForeignKey(
        'plantas_operacion.Receta', on_delete=models.CASCADE, null=True, blank=True,
        related_name='artefactos_externos',
    )
    equipo = models.ForeignKey(
        'recursos.UnidadEquipo', on_delete=models.CASCADE, null=True, blank=True,
        related_name='artefactos_externos',
    )
    area = models.ForeignKey(
        'gestion_unidades.EspacioReservable', on_delete=models.CASCADE, null=True, blank=True,
        related_name='artefactos_externos',
    )
    software_requerido = models.CharField(max_length=180)
    version_software = models.CharField(max_length=80, blank=True)
    licencia_software = models.CharField(
        max_length=20,
        choices=(
            ('libre', 'Libre'), ('academica', 'Académica'),
            ('comercial', 'Comercial'), ('upec', 'Propia UPEC'),
        ),
    )
    requisitos_tecnicos = models.TextField()
    instrucciones_uso = models.TextField()
    archivos = models.ManyToManyField(Recurso, db_table='webcitt_artefactoexterno_archivos', blank=True, related_name='artefactos_externos')
    entradas_esperadas = models.JSONField(default=list, blank=True)
    salidas_devueltas = models.JSONField(default=list, blank=True)
    formato_intercambio = models.CharField(max_length=8, choices=FORMATOS, blank=True)
    esquema = models.JSONField(default=dict, blank=True)
    que_representa = models.TextField()
    supuestos_simplificaciones = models.TextField()
    estado_verificacion = models.CharField(
        max_length=16,
        choices=(('sin_verificar', 'Sin verificar'), ('verificado', 'Verificado')),
        default='sin_verificar',
    )
    estado_validacion = models.CharField(max_length=16, choices=ESTADOS_VALIDACION, default='sin_validar')
    evidencia_validacion = models.ForeignKey(
        Recurso, on_delete=models.PROTECT, null=True, blank=True,
        related_name='artefactos_validados',
    )
    fuente_referencia = models.CharField(
        max_length=500,
        blank=True,
        help_text='URL, DOI, acta, informe o identificador de la fuente que respalda el artefacto.',
    )
    responsable_validacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='artefactos_externos_validados',
        editable=False,
    )
    validado_en = models.DateTimeField(null=True, blank=True, editable=False)
    vigente_desde = models.DateField(null=True, blank=True)
    vigente_hasta = models.DateField(null=True, blank=True)
    limitaciones_conocidas = models.TextField()
    autor = models.CharField(max_length=180)
    institucion = models.CharField(max_length=180, default='Universidad Politécnica Estatal del Carchi')
    contacto = models.CharField(max_length=180, blank=True)
    licencia_uso = models.CharField(max_length=120)
    cita_requerida = models.BooleanField(default=True)
    version = models.PositiveSmallIntegerField(default=1)
    reemplaza_a = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='versiones_nuevas',
    )
    estado = models.CharField(max_length=16, choices=ESTADOS, default='borrador', db_index=True)
    visibilidad = models.CharField(max_length=20, choices=VISIBILIDADES_CONTENIDO, default='interna')
    posiblemente_desactualizado = models.BooleanField(default=False, db_index=True)
    motivo_desactualizacion = models.CharField(max_length=255, blank=True)
    sincronizado_en = models.DateTimeField(null=True, blank=True)
    veces_descargado = models.PositiveIntegerField(default=0, editable=False)
    ultima_ejecucion = models.DateTimeField(null=True, blank=True, editable=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_artefactoexterno'
        ordering = ('unidad', 'familia__orden', 'nombre')
        verbose_name = 'Artefacto externo'
        verbose_name_plural = 'Artefactos externos'

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    def clean(self):
        super().clean()
        errores = {}
        if self.codigo and not PATRON_CODIGO_ARTEFACTO.fullmatch(self.codigo):
            errores['codigo'] = 'El código del artefacto debe usar el formato PLANTA-SIM-OBJETO.'
        elif self.codigo:
            prefijo = self.codigo.split('-', 1)[0]
            relaciones = (
                self.familia,
                self.receta,
                self.equipo,
                self.area,
            )
            for relacion in relaciones:
                codigo_relacion = getattr(relacion, 'codigo', '') or getattr(
                    relacion, 'codigo_unidad', '',
                )
                if codigo_relacion and codigo_relacion.split('-', 1)[0] != prefijo:
                    errores['codigo'] = 'El prefijo del artefacto debe coincidir con sus relaciones.'
                    break
        for relacion in (self.receta, self.area):
            if relacion is not None and relacion.unidad_id != self.unidad_id:
                errores['unidad'] = 'La receta, el equipo y el área deben pertenecer a la misma unidad.'
        if self.equipo_id:
            pertenece = (
                self.equipo.laboratorio_id == self.unidad_id
                or self.equipo.laboratorios.filter(pk=self.unidad_id).exists()
            )
            if not pertenece:
                errores['unidad'] = 'La receta, el equipo y el área deben pertenecer a la misma unidad.'
        if self.familia_id and self.familia.unidad_id != self.unidad_id:
            errores['familia'] = 'La familia debe pertenecer a la misma unidad.'
        if self.evidencia_validacion_id and self.evidencia_validacion.unidad_id != self.unidad_id:
            errores['evidencia_validacion'] = 'La evidencia debe pertenecer a la misma unidad.'
        if self.vigente_desde and self.vigente_hasta and self.vigente_hasta < self.vigente_desde:
            errores['vigente_hasta'] = 'La fecha final de vigencia no puede ser anterior a la inicial.'
        if self.nivel_integracion in (1, 2):
            if not self.entradas_esperadas:
                errores['entradas_esperadas'] = 'Un artefacto conectado declara los campos que consume.'
            if not self.salidas_devueltas:
                errores['salidas_devueltas'] = 'Un artefacto conectado declara las medidas que devuelve.'
            if not self.formato_intercambio:
                errores['formato_intercambio'] = 'Seleccione el formato del contrato de datos.'
            if not self.esquema:
                errores['esquema'] = 'Declare el esquema legible por máquina.'
        if self.estado == 'publicado':
            obligatorios = {
                'que_representa': self.que_representa,
                'supuestos_simplificaciones': self.supuestos_simplificaciones,
                'estado_validacion': self.estado_validacion != 'sin_validar',
                'evidencia_validacion': self.evidencia_validacion_id,
                'fuente_referencia': self.fuente_referencia,
                'responsable_validacion': self.responsable_validacion_id,
                'validado_en': self.validado_en,
                'vigente_desde': self.vigente_desde,
                'limitaciones_conocidas': self.limitaciones_conocidas,
                'instrucciones_uso': self.instrucciones_uso,
            }
            for campo, valor in obligatorios.items():
                if not valor:
                    errores[campo] = 'Este dato es obligatorio antes de publicar el artefacto.'
            if self.vigente_hasta and self.vigente_hasta < timezone.localdate():
                errores['vigente_hasta'] = 'Un artefacto vencido no puede permanecer publicado.'
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        if (
            self.estado_validacion != 'sin_validar'
            and self.responsable_validacion_id
            and not self.validado_en
        ):
            self.validado_en = timezone.now()
        self.full_clean()
        if self.reemplaza_a_id:
            type(self).objects.filter(pk=self.reemplaza_a_id).update(estado='archivado')
        if self.estado == 'publicado' and not self.sincronizado_en:
            self.sincronizado_en = timezone.now()
        super().save(*args, **kwargs)

    @property
    def publicable(self):
        from apps.plantas_piloto.domain.repositorio import esta_vigente

        return (
            self.estado == 'publicado'
            and self.visibilidad in ('publica', 'restringida')
            and esta_vigente(
                timezone.localdate(),
                self.vigente_desde,
                self.vigente_hasta,
                desactualizado=self.posiblemente_desactualizado,
            )
        )

    @property
    def estado_vigencia(self):
        from apps.plantas_piloto.domain.repositorio import estado_vigencia

        return estado_vigencia(
            timezone.localdate(),
            self.vigente_desde,
            self.vigente_hasta,
            desactualizado=self.posiblemente_desactualizado,
        )

    @property
    def cita(self):
        return (
            f'{self.autor}. ({self.actualizado_en.year if self.actualizado_en else timezone.now().year}). '
            f'{self.nombre} (versión {self.version}). {self.institucion}. {self.codigo}.'
        )


def ruta_resultado_artefacto(instancia, nombre):
    extension = Path(nombre).suffix.lower()
    return f'artefactos/resultados/{instancia.artefacto.codigo}/{timezone.now():%Y%m%d-%H%M%S}{extension}'


class ResultadoArtefacto(models.Model):
    artefacto = models.ForeignKey(ArtefactoExterno, on_delete=models.CASCADE, related_name='resultados')
    archivo = models.FileField(upload_to=ruta_resultado_artefacto)
    resumen = models.JSONField(default=dict, blank=True)
    importado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='resultados_artefacto_importados',
    )
    importado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_resultadoartefacto'
        ordering = ('-importado_en',)

    def __str__(self):
        return f'{self.artefacto.codigo} · {self.importado_en:%d/%m/%Y %H:%M}'

    def clean(self):
        super().clean()
        if not self.archivo or not self.artefacto_id:
            return
        extension = Path(self.archivo.name).suffix.lower().lstrip('.')
        esperado = self.artefacto.formato_intercambio
        if esperado and extension != esperado:
            raise ValidationError({'archivo': f'El contrato de datos exige un archivo {esperado.upper()}.'})
