"""Evidencia de gestión y conciliaciones independientes para medir las metas."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class EvidenciaGestionUnidad(models.Model):
    TIPOS = [('USO', 'Conciliación de sesiones observadas'),
             ('DESECHOS', 'Conciliación de partidas de desechos generadas'),
             ('INVENTARIO', 'Acta de revisión de equipos, software y espacios'),
             ('CAPACITACION', 'Capacitación recibida por el personal'),
             ('DIFUSION', 'Publicación, evento o material difundido'),
             ('INVESTIGACION', 'Resultado de investigación o desarrollo tecnológico'),
             ('TRANSFERENCIA', 'Transferencia o servicio especializado aceptado'),
             ('INSPECCION', 'Inspección de seguridad y condiciones de operación'),
             ('PLAN-INFRA', 'Plan de mantenimiento de infraestructura'),
             ('EJECUCION-INFRA', 'Informe de ejecución del mantenimiento de infraestructura'),
             ('FUNCIONALIDAD', 'Verificación funcional documentada de equipos'),
             ('BOLETINES', 'Boletín o informe publicado'), ('EVENTOS', 'Evento realizado'),
             ('PROYECTOS', 'Proyecto de investigación en ejecución'),
             ('PUBLICACIONES', 'Artículo o ponencia publicados'),
             ('ENSAYOS', 'Ensayo establecido y evaluado'), ('PRODUCCION', 'Proceso o lote cerrado')]
    ESTADOS = [('borrador', 'Borrador'), ('validado', 'Evidencia verificada'), ('anulado', 'Rectificado')]
    unidad = models.ForeignKey('directorio_unidades.Unidad', on_delete=models.PROTECT,
                              related_name='evidencias_gestion')
    codigo = models.CharField(max_length=60)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    fecha = models.DateField(default=timezone.localdate)
    titulo = models.CharField(max_length=180)
    descripcion = models.TextField()
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    recurso = models.ForeignKey('recursos.Recurso', on_delete=models.PROTECT, null=True, blank=True,
                               related_name='evidencias_gestion')
    enlace = models.URLField(blank=True, help_text='Publicación o evidencia verificable.')
    desde = models.DateField(null=True, blank=True)
    hasta = models.DateField(null=True, blank=True)
    total_observado = models.PositiveIntegerField(null=True, blank=True,
        help_text='Universo del acta o bitácora independiente, no el total calculado por el sistema.')
    alcance = models.JSONField(default=list, blank=True)
    detalle = models.JSONField(default=dict, blank=True,
        help_text='Resultado, aceptación o inspección documentada con su alcance y seguimiento.')
    estado = models.CharField(max_length=10, choices=ESTADOS, default='borrador')
    demostracion = models.BooleanField(default=False, editable=False)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    creado_en = models.DateTimeField(auto_now_add=True)
    validado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    null=True, blank=True, related_name='+')
    validado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha', '-pk']
        constraints = [models.UniqueConstraint(fields=['unidad', 'codigo'], name='evidencia_gestion_codigo_unico'),
            models.UniqueConstraint(fields=['unidad', 'tipo', 'recurso'],
                condition=models.Q(estado='validado', recurso__isnull=False), name='evidencia_fuente_archivo_unica'),
            models.UniqueConstraint(fields=['unidad', 'tipo', 'enlace'],
                condition=models.Q(estado='validado') & ~models.Q(enlace=''), name='evidencia_fuente_enlace_unica')]
        indexes = [models.Index(fields=['unidad', 'tipo', 'estado', 'fecha'], name='evidencia_gestion_medicion')]
        verbose_name = 'Evidencia de gestión de la unidad'

    def __str__(self):
        return f'{self.codigo} · {self.titulo}'

    def clean(self):
        super().clean()
        errores = {}
        if self.fecha and self.fecha > timezone.localdate():
            errores['fecha'] = 'Una evidencia realizada no puede tener fecha futura.'
        if not (self.titulo or '').strip() or not (self.descripcion or '').strip():
            errores['descripcion'] = 'Describe la actividad y su resultado; una evidencia vacía no acredita la meta.'
        if self.recurso_id and (self.recurso.unidad_id != self.unidad_id or not self.recurso.activo or not self.recurso.archivo
                                or not self.recurso.hash_sha256):
            errores['recurso'] = 'El archivo debe pertenecer a esta unidad y tener contenido y huella registrados.'
        elif self.recurso_id:
            from .respaldo_medicion import validar_respaldo
            try:
                if validar_respaldo(self.recurso.archivo) != self.recurso.hash_sha256:
                    raise ValidationError('El contenido del archivo cambió; registra una evidencia nueva.')
            except ValidationError as error:
                errores['recurso'] = error.messages
        if self.responsable_id and self.unidad_id:
            from apps.gestion_unidades.models.espacios import ResponsableUnidad
            if (self.unidad.administrador_id != self.responsable_id and not
                    ResponsableUnidad.objects.filter(unidad_id=self.unidad_id,
                        usuario_id=self.responsable_id, activo=True).exists()):
                errores['responsable'] = 'El responsable debe formar parte de esta unidad.'
        if self.tipo in ('USO', 'DESECHOS'):
            if not self.desde or not self.hasta or self.total_observado is None:
                errores['total_observado'] = 'Indica el tramo y el total observado en la fuente independiente.'
            elif self.desde > self.hasta or self.hasta > self.fecha:
                errores['hasta'] = 'El tramo debe estar ordenado y terminar a más tardar en la fecha del acta.'
        if self.tipo == 'INVENTARIO':
            from .respaldo_medicion import alcances_inventario
            esperados = alcances_inventario(self.unidad)
            if (not isinstance(self.alcance, list) or
                    any(not isinstance(clave, str) for clave in self.alcance) or
                    sorted(self.alcance) != sorted(esperados)):
                errores['alcance'] = ('El acta integral debe comprobar equipos informáticos, software y espacios.'
                    if 'insumos' not in esperados else
                    'El acta integral debe comprobar equipos, software, espacios y reactivos e insumos.')
        if self.estado == 'validado':
            from .resultados_gestion import errores_resultado
            # Con la unidad, una inspección solo admite las condiciones de su tipo.
            resultado = errores_resultado(self.tipo, self.detalle, self.fecha,
                                          unidad=self.unidad if self.unidad_id else None)
            if resultado:
                errores['__all__'] = list(resultado.values())
            if not self.recurso_id and not self.enlace:
                errores['recurso'] = 'Adjunta un archivo de la unidad o el enlace de la evidencia.'
            if not self.validado_por_id or not self.validado_en:
                errores['estado'] = 'La verificación debe registrar quién y cuándo la realizó.'
        from .infraestructura import errores_relaciones_infraestructura
        relaciones = errores_relaciones_infraestructura(self)
        if relaciones:
            errores.setdefault('__all__', []).extend(relaciones.pop('__all__', []))
            errores.update(relaciones)
        from .funcionalidad import errores_relaciones_funcionalidad
        relaciones = errores_relaciones_funcionalidad(self)
        if relaciones:
            errores.setdefault('__all__', []).extend(relaciones.pop('__all__', []))
            errores.update(relaciones)
        if errores:
            raise ValidationError(errores)
