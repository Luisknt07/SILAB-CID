"""Calendario académico institucional y vinculación histórica de usuarios."""

from apps.core.calendario import TIPOS_PERIODO
from apps.core.presentation.calendario import (
    ambitos, ambitos_operacion, ambito_predeterminado, calendario_actual, ciclos, semanas_predeterminadas,
)
from apps.core.presentation.niveles import niveles

from apps.core.presentation.catalogos import tipos_con_carrera, tipos_usuario

from apps.core.presentation.catalogos import carreras, facultades

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.core.models.usuarios_base import UserProfile


class PeriodoAcademicoQuerySet(models.QuerySet):
    def operativos(self):
        return self.filter(ambito__in=ambitos_operacion())

    def publicados(self):
        return self.filter(estado__in=("publicado", "cerrado"))

    def para_fecha(self, fecha, *, ambito=None):
        queryset = self.publicados().filter(
            versiones__vigente=True,
            versiones__fecha_inicio_clases__lte=fecha,
            versiones__fecha_fin_periodo__gte=fecha,
        )
        if ambito:
            queryset = queryset.filter(ambito=ambito)
        return queryset.distinct().order_by("-versiones__fecha_inicio_clases", "-pk")


class PeriodoAcademico(models.Model):
    """Identidad estable de un PAO, independiente de sus reformas."""

    ESTADO_CHOICES = [
        ("borrador", "Borrador"),
        ("publicado", "Publicado"),
        ("cerrado", "Cerrado"),
    ]

    codigo = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text=(
            "Código institucional estable, por ejemplo 2026-A, 2026-B, "
            "2026-I1 o 2026-E1."
        ),
    )
    nombre = models.CharField(max_length=120, blank=True)
    anio_referencia = models.PositiveSmallIntegerField(db_index=True)
    ciclo = models.CharField(max_length=1, choices=ciclos, db_index=True)
    tipo = models.CharField(max_length=20, choices=TIPOS_PERIODO, default="ordinario")
    ambito = models.CharField(
        max_length=30,
        choices=ambitos,
        default=ambito_predeterminado,
        db_index=True,
    )
    semanas_planificadas = models.PositiveSmallIntegerField(
        default=semanas_predeterminadas,
        help_text="Número de semanas establecido por el calendario aprobado.",
    )
    estado = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default="borrador",
        db_index=True,
    )
    observaciones = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    objects = PeriodoAcademicoQuerySet.as_manager()

    class Meta:
        db_table = 'webcitt_periodoacademico'
        ordering = ["-anio_referencia", "-ciclo", "codigo"]
        verbose_name = "Período académico"
        verbose_name_plural = "Períodos académicos"
        constraints = [
            models.CheckConstraint(
                check=Q(semanas_planificadas__gte=1) & Q(semanas_planificadas__lte=24),
                name="periodo_semanas_entre_1_y_24",
            ),
        ]

    def __str__(self):
        return self.nombre or self.codigo

    def clean(self):
        errors = {}
        codigo = (self.codigo or "").strip().upper()
        if codigo and not codigo.startswith(str(self.anio_referencia)):
            errors["codigo"] = "El código debe comenzar con el año de referencia."
        politica = calendario_actual()
        if politica.tipo_para_ciclo(self.ciclo) != self.tipo:
            errors["ciclo"] = "El ciclo no corresponde al tipo de periodo seleccionado."
        if self._state.adding and self.ciclo not in {c for c, _, _ in politica.ciclos}:
            errors["ciclo"] = "Selecciona un ciclo activo para crear un periodo."
        if self._state.adding and self.ambito not in dict(politica.ambitos):
            errors["ambito"] = "Selecciona un ambito activo para crear un periodo."
        if self.semanas_planificadas is not None and not politica.semanas_minimas <= self.semanas_planificadas <= politica.semanas_maximas:
            errors["semanas_planificadas"] = "Las semanas no corresponden a la politica institucional vigente."
        if self.estado in {"publicado", "cerrado"} and self.pk:
            if not self.versiones.filter(vigente=True).exists():
                errors["estado"] = "Para publicar o cerrar el período debe existir una versión vigente."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.codigo = (self.codigo or "").strip().upper()
        if not self.nombre:
            self.nombre = f"Período académico {self.codigo}"
        super().save(*args, **kwargs)

    @property
    def version_vigente(self):
        prefetched = getattr(self, "_prefetched_objects_cache", {}).get("versiones")
        if prefetched is not None:
            return next((version for version in prefetched if version.vigente), None)
        return self.versiones.filter(vigente=True).first()

    def semana_para_fecha(self, fecha):
        version = self.version_vigente
        if not version:
            return None
        return version.semanas.filter(fecha_inicio__lte=fecha, fecha_fin__gte=fecha).first()


class VersionCalendarioAcademico(models.Model):
    """Versión aprobada del calendario; conserva reformas sin alterar la historia."""

    periodo = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.PROTECT,
        related_name="versiones",
    )
    numero = models.PositiveSmallIntegerField(default=1)
    nombre = models.CharField(
        max_length=160,
        blank=True,
        help_text="Ejemplo: Calendario original o Primera reforma.",
    )
    fecha_inicio_clases = models.DateField(
        "Inicio de clases o actividades",
        db_index=True,
    )
    fecha_fin_clases = models.DateField("Fin de clases o actividades")
    fecha_fin_periodo = models.DateField(db_index=True)
    fecha_publicacion = models.DateField(null=True, blank=True)
    resolucion = models.CharField(max_length=120, blank=True)
    documento = models.FileField(upload_to="calendarios_academicos/", blank=True)
    fuente_url = models.URLField(blank=True)
    motivo_reforma = models.TextField(blank=True)
    vigente = models.BooleanField(default=True, db_index=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calendarios_academicos_creados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_versioncalendarioacademico'
        ordering = ["periodo", "-numero"]
        verbose_name = "Versión del calendario académico"
        verbose_name_plural = "Versiones de calendarios académicos"
        constraints = [
            models.UniqueConstraint(
                fields=["periodo", "numero"],
                name="version_numero_unico_por_periodo",
            ),
            models.UniqueConstraint(
                fields=["periodo"],
                condition=Q(vigente=True),
                name="una_version_vigente_por_periodo",
            ),
        ]

    def __str__(self):
        etiqueta = self.nombre or f"Versión {self.numero}"
        return f"{self.periodo.codigo} · {etiqueta}"

    def clean(self):
        errors = {}
        if self.fecha_fin_clases < self.fecha_inicio_clases:
            errors["fecha_fin_clases"] = "La finalización de clases no puede preceder al inicio."
        if self.fecha_fin_periodo < self.fecha_fin_clases:
            errors["fecha_fin_periodo"] = "El cierre del período no puede preceder al fin de clases."
        if self.vigente and self.periodo_id:
            vigente = type(self).objects.filter(periodo_id=self.periodo_id, vigente=True)
            if self.pk:
                vigente = vigente.exclude(pk=self.pk)
            if vigente.exists():
                errors["vigente"] = "Ya existe una versión vigente para este período."
        if errors:
            raise ValidationError(errors)


class SemanaAcademica(models.Model):
    TIPO_CHOICES = [
        ("clases", "Clases"),
        ("evaluacion", "Evaluación"),
        ("recuperacion", "Recuperación"),
        ("vacaciones", "Vacaciones"),
        ("suspension", "Suspensión de actividades"),
        ("operacion_interperiodo", "Operación intersemestral"),
        ("otra", "Otra semana institucional"),
    ]

    version_calendario = models.ForeignKey(
        VersionCalendarioAcademico,
        on_delete=models.CASCADE,
        related_name="semanas",
    )
    numero = models.PositiveSmallIntegerField()
    fecha_inicio = models.DateField(db_index=True)
    fecha_fin = models.DateField(db_index=True)
    tipo = models.CharField(max_length=25, choices=TIPO_CHOICES, default="clases")
    parcial = models.PositiveSmallIntegerField(null=True, blank=True)
    reportable = models.BooleanField(default=True)
    permite_reservas = models.BooleanField(default=True)
    observaciones = models.CharField(max_length=240, blank=True)

    class Meta:
        db_table = 'webcitt_semanaacademica'
        ordering = ["version_calendario", "numero"]
        verbose_name = "Semana académica"
        verbose_name_plural = "Semanas académicas"
        constraints = [
            models.UniqueConstraint(
                fields=["version_calendario", "numero"],
                name="numero_semana_unico_por_calendario",
            ),
            models.CheckConstraint(
                check=Q(numero__gte=1) & Q(numero__lte=24),
                name="semana_academica_entre_1_y_24",
            ),
        ]

    def __str__(self):
        return f"{self.version_calendario.periodo.codigo} · Semana {self.numero}"

    def clean(self):
        errors = {}
        if self.fecha_fin < self.fecha_inicio:
            errors["fecha_fin"] = "La fecha final no puede preceder a la inicial."
        version = self.version_calendario if self.version_calendario_id else None
        if version:
            if self.numero > version.periodo.semanas_planificadas:
                errors["numero"] = "La semana supera la cantidad planificada para el período."
            if self.fecha_inicio < version.fecha_inicio_clases:
                errors["fecha_inicio"] = "La semana no puede iniciar antes que el calendario vigente."
            if self.fecha_fin > version.fecha_fin_periodo:
                errors["fecha_fin"] = "La semana no puede terminar después del cierre del período."
        if errors:
            raise ValidationError(errors)


class VinculacionUsuarioPeriodo(models.Model):
    """Clasificación de una persona en un período sin reescribir reportes pasados."""

    ESTADO_CHOICES = [
        ("activa", "Activa"),
        ("inactiva", "Inactiva"),
        ("retirada", "Retirada"),
        ("finalizada", "Finalizada"),
    ]
    FUENTE_CHOICES = [
        ("sistema_academico", "Sistema académico institucional"),
        ("importacion", "Importación autorizada"),
        ("administracion", "Validación administrativa"),
        ("perfil", "Datos tomados del perfil"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vinculaciones_academicas",
    )
    periodo = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.PROTECT,
        related_name="vinculaciones_usuarios",
    )
    tipo_usuario = models.CharField(max_length=20, choices=tipos_usuario)
    facultad = models.CharField(
        max_length=50,
        choices=facultades,
        blank=True,
        db_index=True,
    )
    carrera = models.CharField(
        max_length=50,
        choices=carreras,
        blank=True,
        db_index=True,
    )
    nivel_academico = models.CharField(
        max_length=30,
        choices=niveles,
        blank=True,
    )
    paralelo = models.CharField(max_length=20, blank=True)
    institucion = models.CharField(max_length=200, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default="activa")
    fuente = models.CharField(max_length=25, choices=FUENTE_CHOICES, default="perfil")
    validada = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_vinculacionusuarioperiodo'
        ordering = ["-periodo__anio_referencia", "usuario__username"]
        verbose_name = "Vinculación de usuario por período"
        verbose_name_plural = "Vinculaciones de usuarios por período"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "periodo"],
                name="una_vinculacion_usuario_por_periodo",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} · {self.periodo.codigo}"

    def clean(self):
        errors = {}
        if self.carrera:
            facultad_esperada = UserProfile.facultad_para_carrera(self.carrera)
            if facultad_esperada and self.facultad and facultad_esperada != self.facultad:
                errors["facultad"] = "La facultad no corresponde a la carrera seleccionada."
        if self.tipo_usuario in tipos_con_carrera() and not self.carrera:
            errors["carrera"] = "La vinculación debe identificar la carrera requerida por la institución."
        if errors:
            raise ValidationError(errors)
