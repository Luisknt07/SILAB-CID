"""Planificación, ejecución y trazabilidad de prácticas de laboratorio.

El modelo parte de la actividad ya existente.  No replica asignaturas ni
sílabos: conserva únicamente los datos que exigen los formatos institucionales
de planificación y ejecución.
"""

import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class PlanificacionPractica(models.Model):
    ESTADOS = [
        ("borrador", "Borrador"),
        ("revision", "Pendiente de revisión"),
        ("aprobada", "Aprobada"),
        ("observada", "Devuelta con observaciones"),
        ("archivada", "Archivada"),
    ]
    CATEGORIAS_USO = [
        ("docencia", "Docencia"),
        ("tesis", "Tesis o titulación"),
        ("posgrado", "Posgrado"),
        ("proyecto", "Proyecto de investigación o vinculación"),
        ("servicio", "Servicio técnico"),
        ("otro", "Otro"),
    ]

    codigo = models.CharField(max_length=32, unique=True, editable=False)
    grupo_version = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    numero_version = models.PositiveSmallIntegerField(default=1)
    es_version_vigente = models.BooleanField(default=True, db_index=True)
    actividad = models.ForeignKey(
        'reservas.CatalogoActividadReserva',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="planificaciones_practica",
    )
    guia = models.ForeignKey(
        'reservas.GuiaActividadReserva',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="planificaciones_practica",
    )
    tema_asignatura = models.ForeignKey(
        'formacion.TemaAsignatura',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sesiones',
        help_text='El tema del sílabo previsto para esta sesión.',
    )
    requiere_guia = models.BooleanField(
        default=True,
        help_text=(
            "Indica si esta planificación necesita una guía de práctica aprobada. "
            "Las reservas de uso sin guía y las actividades no docentes no la requieren."
        ),
    )
    unidad = models.ForeignKey(
        'directorio_unidades.Unidad',
        on_delete=models.PROTECT,
        related_name="planificaciones_practica",
    )
    reserva = models.OneToOneField(
        'reservas.Reserva',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planificacion_practica",
    )
    fecha = models.DateField(db_index=True)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    carrera = models.CharField(max_length=180, blank=True)
    semestre = models.CharField(max_length=60, blank=True)
    asignatura = models.CharField(max_length=180)
    docente_tutor = models.CharField(max_length=180)
    tema = models.CharField(max_length=240)
    resultado_aprendizaje = models.TextField()
    estudiantes_planificados = models.PositiveIntegerField(default=1)
    categoria_uso = models.CharField(
        max_length=20,
        choices=CATEGORIAS_USO,
        default="docencia",
        db_index=True,
    )
    responsable_tecnico = models.ForeignKey(
        'gestion_unidades.ResponsableUnidad',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planificaciones_practica",
    )
    observaciones = models.TextField(blank=True)
    estado = models.CharField(max_length=15, choices=ESTADOS, default="borrador", db_index=True)
    observaciones_revision = models.TextField(blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="planificaciones_practica_creadas",
    )
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planificaciones_practica_revisadas",
    )
    revisado_en = models.DateTimeField(null=True, blank=True)
    eliminado_en = models.DateTimeField(null=True, blank=True, db_index=True)
    eliminado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planificaciones_practica_eliminadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_planificacionpractica'
        ordering = ["-fecha", "hora_inicio", "-pk"]
        verbose_name = "Planificación de práctica"
        verbose_name_plural = "Planificaciones de prácticas"
        constraints = [
            models.UniqueConstraint(
                fields=["grupo_version", "numero_version"],
                name="plan_practica_version_unica",
            ),
            models.UniqueConstraint(
                fields=["grupo_version"],
                condition=models.Q(es_version_vigente=True, eliminado_en__isnull=True),
                name="plan_practica_vigente_unica",
            ),
        ]
        indexes = [
            models.Index(fields=["unidad", "fecha", "estado"]),
            models.Index(fields=["actividad", "estado"]),
        ]

    def __str__(self):
        return f"{self.codigo} · {self.tema}"

    @property
    def activa(self):
        return self.eliminado_en is None

    def clean(self):
        errors = {}
        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
            errors["hora_fin"] = "La hora final debe ser posterior a la inicial."
        if self.estudiantes_planificados < 1:
            errors["estudiantes_planificados"] = "Registra al menos un estudiante."
        if self.actividad_id and self.unidad_id:
            actividad_unidad = self.actividad.unidad_id
            if actividad_unidad and actividad_unidad != self.unidad_id:
                errors["actividad"] = "La actividad no pertenece a esta unidad."
        if self.guia_id:
            if not self.actividad_id:
                errors["guia"] = "Una guía solo puede vincularse a una actividad registrada."
            elif self.guia.actividad_id != self.actividad_id:
                errors["guia"] = "La guía debe pertenecer a la actividad seleccionada."
            if self.estado in {"revision", "aprobada"} and (
                not self.guia.activo or self.guia.estado_publicacion != "publicada"
            ):
                errors["guia"] = "Para revisar o aprobar, selecciona una guía publicada."
        elif self.requiere_guia and self.estado in {"revision", "aprobada"}:
            errors["guia"] = "La planificación debe vincular una guía aprobada."
        if self.reserva_id:
            if self.reserva.laboratorio_id != self.unidad_id:
                errors["reserva"] = "La reserva no pertenece a esta unidad."
            if self.reserva.actividad_catalogo_id not in {None, self.actividad_id}:
                errors["reserva"] = "La reserva está vinculada a otra actividad."
        if self.responsable_tecnico_id and self.responsable_tecnico.unidad_id != self.unidad_id:
            errors["responsable_tecnico"] = "El responsable no pertenece a esta unidad."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.codigo:
            year = self.fecha.year if self.fecha else timezone.localdate().year
            prefix = f"PL-{str(year)[-2:]}-"
            last = (
                type(self).objects.filter(codigo__startswith=prefix)
                .order_by("-codigo")
                .values_list("codigo", flat=True)
                .first()
            )
            sequence = int(last.rsplit("-", 1)[-1]) + 1 if last else 1
            self.codigo = f"{prefix}{sequence:04d}"
        super().save(*args, **kwargs)

    def eliminar_logicamente(self, usuario):
        self.eliminado_en = timezone.now()
        self.eliminado_por = usuario
        self.es_version_vigente = False
        if self.estado != "archivada":
            self.estado = "archivada"
        self.save(update_fields=["eliminado_en", "eliminado_por", "es_version_vigente", "estado", "actualizado_en"])


class EjecucionPractica(models.Model):
    RESULTADOS = [
        ("ejecutada", "Ejecutada"),
        ("reprogramada", "Reprogramada"),
        ("cancelada", "Cancelada"),
    ]
    CUMPLIMIENTO = [
        ("si", "Sí"),
        ("parcial", "Parcial"),
        ("no", "No"),
    ]
    ESTADOS = [
        ("borrador", "Borrador"),
        ("revision", "Pendiente de revisión"),
        ("validada", "Validada y cerrada"),
        ("observada", "Devuelta con observaciones"),
    ]

    planificacion = models.OneToOneField(
        PlanificacionPractica,
        on_delete=models.PROTECT,
        related_name="ejecucion",
    )
    fecha_ejecucion = models.DateField(db_index=True)
    hora_inicio_real = models.TimeField(null=True, blank=True)
    hora_fin_real = models.TimeField(null=True, blank=True)
    resultado = models.CharField(max_length=15, choices=RESULTADOS, default="ejecutada", db_index=True)
    motivo = models.TextField(blank=True)
    estudiantes_asistentes = models.PositiveIntegerField(default=0)
    recursos_utilizados = models.TextField(blank=True)
    detalle_operativo = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Fotografía estructurada de participantes, equipos, software, espacios, "
            "servicios e insumos utilizados durante la práctica."
        ),
    )
    tuvo_incidente = models.BooleanField(default=False)
    incidencia = models.ForeignKey(
        'recursos.IncidenciaEquipo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ejecuciones_practica",
    )
    observaciones_docente = models.TextField(blank=True)
    cumplimiento_resultado = models.CharField(max_length=10, choices=CUMPLIMIENTO, blank=True)
    responsable_tecnico = models.ForeignKey(
        'gestion_unidades.ResponsableUnidad',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ejecuciones_practica",
    )
    estado = models.CharField(max_length=15, choices=ESTADOS, default="borrador", db_index=True)
    observaciones_revision = models.TextField(blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ejecuciones_practica_creadas",
    )
    validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ejecuciones_practica_validadas",
    )
    validado_en = models.DateTimeField(null=True, blank=True)
    eliminado_en = models.DateTimeField(null=True, blank=True, db_index=True)
    eliminado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ejecuciones_practica_eliminadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_ejecucionpractica'
        ordering = ["-fecha_ejecucion", "-pk"]
        verbose_name = "Ejecución de práctica"
        verbose_name_plural = "Ejecuciones de prácticas"
        indexes = [models.Index(fields=["fecha_ejecucion", "estado", "resultado"])]

    def __str__(self):
        return f"Ejecución {self.planificacion.codigo}"

    @property
    def es_efectiva(self):
        """Solo una ejecución realizada y validada alimenta indicadores efectivos."""
        return bool(
            self.eliminado_en is None
            and self.estado == "validada"
            and self.resultado == "ejecutada"
        )

    def clean(self):
        errors = {}
        if self.hora_inicio_real and self.hora_fin_real and self.hora_fin_real <= self.hora_inicio_real:
            errors["hora_fin_real"] = "La hora final real debe ser posterior a la inicial."
        if self.resultado in {"reprogramada", "cancelada"} and not self.motivo.strip():
            errors["motivo"] = "Registra el motivo de la reprogramación o cancelación."
        if self.resultado == "ejecutada":
            if not self.hora_inicio_real or not self.hora_fin_real:
                errors["hora_inicio_real"] = "Registra el horario real de la ejecución."
            if not self.cumplimiento_resultado:
                errors["cumplimiento_resultado"] = "Evalúa el resultado de aprendizaje."
        if self.incidencia_id and self.incidencia.unidad_id != self.planificacion.unidad_id:
            errors["incidencia"] = "La incidencia no pertenece a la unidad de la práctica."
        if self.responsable_tecnico_id and self.responsable_tecnico.unidad_id != self.planificacion.unidad_id:
            errors["responsable_tecnico"] = "El responsable no pertenece a esta unidad."
        if errors:
            raise ValidationError(errors)

    def eliminar_logicamente(self, usuario):
        self.eliminado_en = timezone.now()
        self.eliminado_por = usuario
        self.save(update_fields=["eliminado_en", "eliminado_por", "actualizado_en"])


class RegistroAuditoriaUnidad(models.Model):
    ACCIONES = [
        ("crear", "Crear"),
        ("actualizar", "Actualizar"),
        ("enviar", "Enviar a revisión"),
        ("aprobar", "Aprobar o validar"),
        ("observar", "Observar"),
        ("archivar", "Archivar"),
        ("consultar", "Consultar"),
        ("descargar", "Descargar"),
        ("eliminar", "Eliminar"),
    ]

    # La auditoría sobrevive a la unidad: si esta se elimina, el registro conserva su nombre.
    unidad = models.ForeignKey(
        'directorio_unidades.Unidad', on_delete=models.SET_NULL, null=True, blank=True, related_name="auditoria_operativa",
    )
    unidad_nombre = models.CharField(max_length=200, blank=True, editable=False)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=15, choices=ACCIONES, db_index=True)
    entidad = models.CharField(max_length=80, db_index=True)
    objeto_id = models.CharField(max_length=64, blank=True)
    descripcion = models.CharField(max_length=255)
    datos_anteriores = models.JSONField(default=dict, blank=True)
    datos_nuevos = models.JSONField(default=dict, blank=True)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'webcitt_registroauditoriaunidad'
        ordering = ["-creado_en", "-pk"]
        verbose_name = "Registro de auditoría de unidad"
        verbose_name_plural = "Registros de auditoría de unidades"
        indexes = [models.Index(fields=["unidad", "entidad", "creado_en"])]

    def save(self, *args, **kwargs):
        if self.unidad_id and not self.unidad_nombre:
            self.unidad_nombre = self.unidad.nombre
        super().save(*args, **kwargs)

    @property
    def nombre_unidad(self):
        if self.unidad_id:
            return self.unidad.nombre
        return f"{self.unidad_nombre} (unidad eliminada)" if self.unidad_nombre else "Unidad eliminada"

    def __str__(self):
        return f"{self.get_accion_display()} · {self.entidad} · {self.objeto_id}"


def evidencia_practica_upload_to(instance, filename):
    unidad_id = instance.ejecucion.planificacion.unidad_id
    return f"practicas/evidencias/{unidad_id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class EvidenciaPractica(models.Model):
    """Lo que demuestra que la práctica ocurrió: fotografías, informes, productos.

    Cuelga de la ejecución de la práctica. No se sirve por la ruta pública de medios:
    aparecen estudiantes identificados.
    """

    TIPOS = [
        ("fotografia", "Fotografía identificada"),
        ("asistencia", "Registro de asistencia firmado"),
        ("bitacora", "Bitácora"),
        ("captura", "Captura de simulador"),
        ("informe", "Informe de estudiante"),
        ("producto", "Producto desarrollado"),
        ("otro", "Otra evidencia"),
    ]

    ejecucion = models.ForeignKey(EjecucionPractica, on_delete=models.CASCADE, related_name="evidencias")
    tipo = models.CharField(max_length=12, choices=TIPOS)
    archivo = models.FileField(upload_to=evidencia_practica_upload_to, max_length=255)
    nombre_original = models.CharField(max_length=255)
    extension = models.CharField(max_length=20, blank=True)
    tipo_contenido = models.CharField(max_length=120, blank=True)
    tamano = models.PositiveBigIntegerField(default=0)
    descripcion = models.CharField(
        max_length=255,
        help_text="Qué muestra, quiénes aparecen y cuándo se tomó: la identificación que exige la evidencia.",
    )
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="evidencias_practica_subidas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_evidenciapractica'
        ordering = ["tipo", "creado_en", "pk"]
        verbose_name = "Evidencia de práctica"
        verbose_name_plural = "Evidencias de prácticas"

    def __str__(self):
        return f"{self.get_tipo_display()} · {self.nombre_original}"
