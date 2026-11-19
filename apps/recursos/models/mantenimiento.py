"""Mantenimiento, incidencias y trazabilidad del ciclo de vida de equipos."""

import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


def _codigo_orden():
    return f"MNT-{uuid.uuid4().hex[:10].upper()}"


# Estados que pone el sistema mientras dura un bloqueo; nunca son la base a
# la que se vuelve cuando el bloqueo termina.
_ESTADOS_TRANSITORIOS = {"dañado", "mantenimiento", "prestado"}


def _prestamos_afuera(equipo_id):
    """Préstamos con el equipo todavía fuera de la unidad.

    Se resuelve por la aplicación para no importar el modelo: el préstamo
    necesita estos dos ayudantes y esto cerraría el círculo.
    """
    from django.apps import apps

    PrestamoEquipo = apps.get_model('recursos', "PrestamoEquipo")
    return PrestamoEquipo.objects.filter(
        equipo_id=equipo_id, estado__in=PrestamoEquipo.ESTADOS_FUERA)


def estado_base_operativo(equipo):
    """Recupera el estado anterior compartido por bloqueos superpuestos."""
    estados = list(
        IncidenciaEquipo.objects.filter(
            equipo_id=equipo.pk,
            detiene_operacion=True,
        )
        .exclude(estado__in=IncidenciaEquipo.ESTADOS_CERRADOS)
        .exclude(estado_equipo_previo="")
        .order_by("fecha_reporte", "pk")
        .values_list("estado_equipo_previo", flat=True)
    )
    estados.extend(
        MantenimientoEquipo.objects.filter(
            equipo_id=equipo.pk,
            estado="en_proceso",
        )
        .exclude(estado_equipo_previo="")
        .order_by("fecha_inicio", "pk")
        .values_list("estado_equipo_previo", flat=True)
    )
    estados.extend(
        _prestamos_afuera(equipo.pk)
        .exclude(estado_equipo_previo="")
        .order_by("fecha_salida", "pk")
        .values_list("estado_equipo_previo", flat=True)
    )
    for estado in estados:
        if estado not in _ESTADOS_TRANSITORIOS:
            return estado
    if equipo.estado_unidad not in _ESTADOS_TRANSITORIOS:
        return equipo.estado_unidad
    return "disponible"


def sincronizar_estado_operativo(equipo_id, estado_base):
    """Prioriza incidencias, luego mantenimiento, y finalmente restaura la base."""
    hay_incidencia_bloqueante = IncidenciaEquipo.objects.filter(
        equipo_id=equipo_id,
        detiene_operacion=True,
    ).exclude(estado__in=IncidenciaEquipo.ESTADOS_CERRADOS).exists()
    if hay_incidencia_bloqueante:
        estado = "dañado"
    elif MantenimientoEquipo.objects.filter(
        equipo_id=equipo_id,
        estado="en_proceso",
    ).exists():
        estado = "mantenimiento"
    elif _prestamos_afuera(equipo_id).exists():
        estado = "prestado"
    else:
        estado = estado_base if estado_base not in _ESTADOS_TRANSITORIOS else "disponible"
    anterior = UnidadEquipo.objects.filter(pk=equipo_id).values_list("estado_unidad", "laboratorio_id").first()
    UnidadEquipo.objects.filter(pk=equipo_id).update(estado_unidad=estado)
    if anterior and anterior[0] != estado:
        EventoCicloVidaEquipo.objects.create(
            equipo_id=equipo_id,
            unidad_id=anterior[1],
            tipo="cambio_estado",
            estado_anterior=anterior[0],
            estado_nuevo=estado,
            descripcion="Cambio de estado por una incidencia, un mantenimiento o un préstamo.",
        )


EJECUTORES = [
    ("interno", "Personal de la unidad: laboratorista o técnico"),
    ("externo", "Técnico especializado externo o proveedor"),
    ("garantia", "Cubierto por la garantía del proveedor"),
]


class PlanMantenimientoEquipo(models.Model):
    TIPOS = [
        ("preventivo", "Preventivo"),
        ("calibracion", "Calibración"),
        ("inspeccion", "Inspección técnica"),
        ("actualizacion", "Actualización"),
    ]
    EJECUTORES = EJECUTORES

    equipo = models.ForeignKey(
        UnidadEquipo,
        on_delete=models.CASCADE,
        related_name="planes_mantenimiento",
    )
    nombre = models.CharField(max_length=160)
    tipo = models.CharField(max_length=20, choices=TIPOS, default="preventivo")
    frecuencia_dias = models.PositiveIntegerField(
        default=180,
        help_text="Intervalo recomendado entre ejecuciones.",
    )
    fecha_inicio = models.DateField(default=timezone.localdate)
    proxima_ejecucion = models.DateField()
    anticipacion_dias = models.PositiveIntegerField(default=15)
    ejecutor = models.CharField(
        "Quién lo ejecuta",
        max_length=10,
        choices=EJECUTORES,
        default="interno",
        help_text="Un mantenimiento que exige técnico externo se agenda y se presupuesta distinto.",
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planes_mantenimiento_asignados",
    )
    proveedor = models.CharField(max_length=180, blank=True)
    instrucciones = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_planmantenimientoequipo'
        ordering = ["proxima_ejecucion", "equipo__codigo_unidad"]
        verbose_name = "Plan de mantenimiento"
        verbose_name_plural = "Planes de mantenimiento"
        constraints = [
            models.CheckConstraint(
                check=models.Q(frecuencia_dias__gt=0),
                name="plan_mantenimiento_frecuencia_positiva",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} · {self.equipo.codigo_unidad}"

    def clean(self):
        if self.proxima_ejecucion and self.fecha_inicio:
            if self.proxima_ejecucion < self.fecha_inicio:
                raise ValidationError({
                    "proxima_ejecucion": "La próxima ejecución no puede ser anterior al inicio del plan."
                })

    @property
    def esta_vencido(self):
        return self.activo and self.proxima_ejecucion < timezone.localdate()

    @property
    def requiere_programacion(self):
        limite = timezone.localdate() + timedelta(days=self.anticipacion_dias)
        return self.activo and self.proxima_ejecucion <= limite


class IncidenciaEquipo(models.Model):
    TIPOS = [
        ("falla", "Falla o avería"),
        ("seguridad", "Seguridad"),
        ("calibracion", "Desviación de calibración"),
        ("accesorio", "Pérdida o daño de accesorio"),
        ("software", "Software o licencia"),
        ("otro", "Otro"),
    ]
    PRIORIDADES = [
        ("baja", "Baja"),
        ("media", "Media"),
        ("alta", "Alta"),
        ("critica", "Crítica"),
    ]
    ESTADOS = [
        ("abierta", "Abierta"),
        ("evaluacion", "En evaluación"),
        ("reparacion", "En reparación"),
        ("resuelta", "Resuelta"),
        ("cerrada", "Cerrada"),
        ("descartada", "Descartada"),
    ]
    ESTADOS_CERRADOS = {"resuelta", "cerrada", "descartada"}

    # Un incidente de seguridad (una caída, un derrame) puede no involucrar un
    # equipo: entonces se ubica en un espacio de la unidad o en la unidad entera.
    equipo = models.ForeignKey(
        UnidadEquipo,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incidencias",
    )
    espacio = models.ForeignKey(
        'gestion_unidades.EspacioReservable',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incidencias_seguridad",
        help_text="Lugar del incidente de seguridad cuando no involucra un equipo.",
    )
    reserva = models.ForeignKey(
        'reservas.Reserva',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incidencias_operativas",
        help_text="Atencion durante la cual se detecto la incidencia, si aplica.",
    )
    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incidencias_equipos",
        editable=False,
        help_text="Unidad responsable al momento del reporte.",
    )
    titulo = models.CharField(max_length=180)
    tipo = models.CharField(max_length=20, choices=TIPOS, default="falla")
    prioridad = models.CharField(max_length=10, choices=PRIORIDADES, default="media")
    estado = models.CharField(max_length=15, choices=ESTADOS, default="abierta")
    descripcion = models.TextField()
    detiene_operacion = models.BooleanField(default=False)
    estado_equipo_previo = models.CharField(
        max_length=20,
        blank=True,
        editable=False,
        help_text="Estado del equipo antes de que la incidencia detuviera su operación.",
    )
    reportada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incidencias_equipos_reportadas",
    )
    asignada_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incidencias_equipos_asignadas",
    )
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    fecha_hecho = models.DateTimeField(
        "Fecha y hora del hecho",
        default=timezone.now,
        help_text="Cuándo ocurrió; por omisión, cuando se reporta. No puede ser futura.",
    )
    fecha_resolucion = models.DateTimeField(null=True, blank=True, editable=False)
    solucion = models.TextField(blank=True)
    evidencia = models.FileField(upload_to="equipos/incidencias/", blank=True)

    class Meta:
        db_table = 'webcitt_incidenciaequipo'
        ordering = ["-fecha_reporte"]
        verbose_name = "Incidencia de equipo"
        verbose_name_plural = "Incidencias de equipos"
        indexes = [
            models.Index(fields=["estado", "prioridad"]),
            models.Index(fields=["equipo", "fecha_reporte"]),
        ]

    def __str__(self):
        return f"{self.lugar} · {self.titulo}"

    @property
    def lugar(self):
        """Dónde ocurrió: el código del equipo, el espacio o la unidad entera."""
        if self.equipo_id:
            return self.equipo.codigo_unidad
        if self.espacio_id:
            return self.espacio.nombre
        return "Unidad"

    def clean(self):
        errores = {}
        if not self.equipo_id and self.tipo != "seguridad":
            errores["equipo"] = "Elige el equipo: solo un incidente de seguridad se registra sin equipo."
        if self.espacio_id and self.tipo != "seguridad":
            errores["espacio"] = "El espacio se indica solo en los incidentes de seguridad."
        if not self.equipo_id and self.detiene_operacion:
            errores["detiene_operacion"] = "Detener la operación se refiere a un equipo: elígelo o desmarca la opción."
        if not self.equipo_id and not self.unidad_id:
            errores["unidad"] = "Indica la unidad del incidente."
        if self.espacio_id and self.unidad_id and self.espacio.unidad_id != self.unidad_id:
            errores["espacio"] = "El espacio no es de la unidad del incidente."
        if self.fecha_hecho and self.fecha_hecho > timezone.now() + timedelta(minutes=1):
            errores["fecha_hecho"] = "La fecha del hecho no puede ser futura."
        if errores:
            raise ValidationError(errores)
        if self.reserva_id and self.equipo_id:
            unidad_id = self.reserva.laboratorio_id
            pertenece = (
                self.equipo.laboratorio_id == unidad_id
                or self.equipo.laboratorios.filter(pk=unidad_id).exists()
            )
            if not pertenece:
                raise ValidationError({"reserva": "La reserva y el equipo deben pertenecer a la misma unidad."})
        if self.estado in {"resuelta", "cerrada"} and not self.solucion.strip():
            raise ValidationError({"solucion": "Registre la solución antes de cerrar la incidencia."})
        if self.pk and self.estado in {'resuelta', 'cerrada'}:
            diagnostico = DiagnosticoIncidenciaEquipo.objects.filter(incidencia_id=self.pk).first()
            if diagnostico and diagnostico.decision in {'reparar', 'repuesto'} and not self.mantenimientos.filter(estado='completado', resultado_operativo='apto').exclude(prueba_funcionamiento='').exists():
                raise ValidationError({'solucion': 'Antes de resolver la falla diagnosticada, registra una orden completada con prueba de funcionamiento apta.'})

    @property
    def abierta(self):
        return self.estado not in self.ESTADOS_CERRADOS

    def save(self, *args, **kwargs):
        creada = self.pk is None
        if not self.unidad_id:
            if self.equipo_id:
                self.unidad = self.equipo.laboratorio
            elif self.espacio_id:
                self.unidad_id = self.espacio.unidad_id
        if self.estado in self.ESTADOS_CERRADOS and not self.fecha_resolucion:
            self.fecha_resolucion = timezone.now()
        elif self.estado not in self.ESTADOS_CERRADOS:
            self.fecha_resolucion = None

        with transaction.atomic():
            equipo = (UnidadEquipo.objects.select_for_update().get(pk=self.equipo_id)
                      if self.equipo_id else None)
            anterior = None
            if not creada:
                anterior = type(self).objects.select_for_update().get(pk=self.pk)
            era_bloqueante = bool(
                anterior
                and anterior.detiene_operacion
                and anterior.estado not in self.ESTADOS_CERRADOS
            )
            es_bloqueante = self.detiene_operacion and self.abierta
            if es_bloqueante and not era_bloqueante and equipo is not None:
                self.estado_equipo_previo = estado_base_operativo(equipo)

            self.full_clean()
            super().save(*args, **kwargs)
            if self.equipo_id and (era_bloqueante or es_bloqueante):
                sincronizar_estado_operativo(
                    self.equipo_id,
                    self.estado_equipo_previo or "disponible",
                )
            if creada and self.equipo_id:
                EventoCicloVidaEquipo.objects.get_or_create(
                    incidencia=self,
                    tipo="incidencia",
                    defaults={
                        "equipo": self.equipo,
                        "unidad": self.unidad,
                        "usuario": self.reportada_por,
                        "descripcion": self.descripcion,
                    },
                )
            if self.equipo_id and (
                anterior
                and anterior.estado not in self.ESTADOS_CERRADOS
                and self.estado in self.ESTADOS_CERRADOS
            ):
                EventoCicloVidaEquipo.objects.get_or_create(
                    incidencia=self,
                    tipo="incidencia_resuelta",
                    defaults={
                        "equipo": self.equipo,
                        "unidad": self.unidad,
                        "usuario": self.asignada_a,
                        "descripcion": self.solucion,
                    },
                )


class MantenimientoEquipo(models.Model):
    EJECUTORES = EJECUTORES
    TIPOS = [
        ("preventivo", "Preventivo"),
        ("correctivo", "Correctivo"),
        ("calibracion", "Calibración"),
        ("inspeccion", "Inspección técnica"),
        ("actualizacion", "Actualización"),
    ]
    ESTADOS = [
        ("planificado", "Planificado"),
        ("programado", "Programado"),
        ("en_proceso", "En proceso"),
        ("completado", "Completado"),
        ("cancelado", "Cancelado"),
    ]

    codigo = models.CharField(max_length=20, unique=True, default=_codigo_orden, editable=False)
    equipo = models.ForeignKey(
        UnidadEquipo,
        on_delete=models.PROTECT,
        related_name="mantenimientos",
    )
    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mantenimientos_equipos",
        editable=False,
    )
    plan = models.ForeignKey(
        PlanMantenimientoEquipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ejecuciones",
    )
    incidencia = models.ForeignKey(
        IncidenciaEquipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mantenimientos",
    )
    tipo = models.CharField(max_length=20, choices=TIPOS, default="preventivo")
    estado = models.CharField(max_length=15, choices=ESTADOS, default="planificado")
    titulo = models.CharField(max_length=180)
    descripcion = models.TextField(blank=True)
    fecha_programada = models.DateTimeField()
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mantenimientos_equipos_asignados",
    )
    ejecutor = models.CharField(
        "Quién lo ejecutó",
        max_length=10,
        choices=EJECUTORES,
        default="interno",
    )
    proveedor = models.CharField(max_length=180, blank=True)
    costo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    duracion_horas = models.PositiveSmallIntegerField(
        "Duración prevista (horas)",
        default=2,
        help_text="Cuánto tiempo queda tomado el equipo. Con esto se reserva en el calendario.",
    )
    bloquea_agenda = models.BooleanField(
        "Reservar el equipo en el calendario",
        default=True,
        help_text="Cierra esas horas en la agenda para que nadie reserve el equipo mientras se interviene.",
    )
    resultado = models.TextField(blank=True)
    prueba_funcionamiento = models.TextField(blank=True, help_text='Prueba realizada, resultado y persona que verifica el retorno al servicio.')
    resultado_operativo = models.CharField(max_length=12, choices=[('pendiente', 'Por verificar'), ('apto', 'Apto para operar'), ('parcial', 'Operación limitada'), ('no_apto', 'No apto para operar')], default='pendiente')
    proximo_mantenimiento = models.DateField(null=True, blank=True)
    estado_equipo_previo = models.CharField(
        max_length=20,
        blank=True,
        editable=False,
        help_text="Estado del equipo antes de iniciar el mantenimiento.",
    )
    informe = models.FileField(upload_to="equipos/mantenimientos/", blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_mantenimientoequipo'
        ordering = ["-fecha_programada"]
        verbose_name = "Mantenimiento de equipo"
        verbose_name_plural = "Mantenimientos de equipos"
        indexes = [
            models.Index(fields=["estado", "fecha_programada"]),
            models.Index(fields=["equipo", "fecha_programada"]),
        ]

    def __str__(self):
        return f"{self.codigo} · {self.equipo.codigo_unidad}"

    def clean(self):
        if self.plan_id and self.plan.equipo_id != self.equipo_id:
            raise ValidationError({"plan": "El plan pertenece a otro equipo."})
        if self.incidencia_id and self.incidencia.equipo_id != self.equipo_id:
            raise ValidationError({"incidencia": "La incidencia pertenece a otro equipo."})
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError({"fecha_fin": "La fecha de fin no puede ser anterior al inicio."})
        if self.estado == "completado" and not self.resultado.strip():
            raise ValidationError({"resultado": "Registre el resultado del mantenimiento."})
        if self.estado == 'completado' and self.incidencia_id and DiagnosticoIncidenciaEquipo.objects.filter(incidencia_id=self.incidencia_id).exists():
            errores = {}
            if not self.prueba_funcionamiento.strip():
                errores['prueba_funcionamiento'] = 'Registra la prueba de funcionamiento antes de completar la intervención diagnosticada.'
            if self.resultado_operativo == 'pendiente':
                errores['resultado_operativo'] = 'Declara si el equipo puede volver a operar; completar la orden no acredita por sí solo que esté reparado.'
            if not self.fecha_inicio:
                errores['fecha_inicio'] = 'Registra el inicio real de la intervención.'
            if errores:
                raise ValidationError(errores)

    def save(self, *args, **kwargs):
        creada = self.pk is None
        if not self.unidad_id:
            self.unidad = self.equipo.laboratorio
        if self.estado == "en_proceso" and not self.fecha_inicio:
            self.fecha_inicio = timezone.now()
        if self.estado == "completado" and not self.fecha_fin:
            self.fecha_fin = timezone.now()

        with transaction.atomic():
            equipo = UnidadEquipo.objects.select_for_update().get(pk=self.equipo_id)
            anterior = None
            if not creada:
                anterior = type(self).objects.select_for_update().get(pk=self.pk)
            estado_anterior = anterior.estado if anterior else None
            estaba_en_proceso = estado_anterior == "en_proceso"
            esta_en_proceso = self.estado == "en_proceso"
            if esta_en_proceso and not estaba_en_proceso:
                self.estado_equipo_previo = estado_base_operativo(equipo)

            self.full_clean()
            super().save(*args, **kwargs)
            if estado_anterior != "completado" and self.estado == "completado":
                fecha_realizada = timezone.localtime(self.fecha_fin).date()
                proxima = self.proximo_mantenimiento
                if self.plan_id and not proxima:
                    proxima = fecha_realizada + timedelta(days=self.plan.frecuencia_dias)
                cambios = {"fecha_ultimo_mantenimiento": fecha_realizada}
                if proxima:
                    cambios["proximo_mantenimiento"] = proxima
                UnidadEquipo.objects.filter(pk=self.equipo_id).update(**cambios)
                if self.plan_id:
                    PlanMantenimientoEquipo.objects.filter(pk=self.plan_id).update(
                        proxima_ejecucion=proxima
                    )
                EventoCicloVidaEquipo.objects.get_or_create(
                    mantenimiento=self,
                    tipo="mantenimiento",
                    defaults={
                        "equipo": self.equipo,
                        "unidad": self.unidad,
                        "usuario": self.responsable,
                        "descripcion": self.resultado,
                    },
                )
                if self.tipo == "calibracion":
                    self._registrar_calibracion(fecha_realizada)
            if estaba_en_proceso or esta_en_proceso or (self.estado == 'completado' and self.resultado_operativo in {'no_apto', 'parcial'}):
                sincronizar_estado_operativo(
                    self.equipo_id,
                    'no_disponible' if self.estado == 'completado' and self.resultado_operativo in {'no_apto', 'parcial'} else (self.estado_equipo_previo or "disponible"),
                )
            self.sincronizar_bloqueo_de_agenda()

    def _registrar_calibracion(self, fecha_realizada):
        """La orden de calibración completada actualiza la calibración del equipo físico.

        Última = fin real; próxima = la indicada en la orden o la frecuencia del plan de calibración del
        equipo; si no hay ninguna, queda la anterior (o vacía si ya quedó atrás). El informe de la orden se
        copia como certificado del equipo, para que no dependa de la vida de la orden. Deja rastro en el
        ciclo de vida del equipo y en la auditoría de la unidad.
        """
        from django.core.files.base import ContentFile

        equipo = UnidadEquipo.objects.select_for_update().get(pk=self.equipo_id)
        plan = self.plan if self.plan_id and self.plan.tipo == "calibracion" else None
        if plan is None:
            vigentes = list(PlanMantenimientoEquipo.objects.filter(
                equipo_id=self.equipo_id, activo=True, tipo="calibracion")[:2])
            plan = vigentes[0] if len(vigentes) == 1 else None
        proxima = self.proximo_mantenimiento or (
            fecha_realizada + timedelta(days=plan.frecuencia_dias) if plan else equipo.proxima_calibracion)
        if proxima and proxima <= fecha_realizada:
            proxima = None
        anteriores = {
            "ultima_calibracion": str(equipo.ultima_calibracion or ""),
            "proxima_calibracion": str(equipo.proxima_calibracion or ""),
            "certificado_calibracion": equipo.certificado_calibracion.name or "",
        }
        equipo.ultima_calibracion, equipo.proxima_calibracion = fecha_realizada, proxima
        campos = ["ultima_calibracion", "proxima_calibracion"]
        if self.informe:
            extension = (self.informe.name.rsplit(".", 1)[-1] if "." in self.informe.name else "pdf").lower()
            with self.informe.open("rb") as origen:
                contenido = origen.read()
            equipo.certificado_calibracion.save(
                f"{equipo.codigo_unidad}-{self.codigo}.{extension}", ContentFile(contenido), save=False)
            campos.append("certificado_calibracion")
        UnidadEquipo.objects.filter(pk=equipo.pk).update(**{campo: getattr(equipo, campo) for campo in campos})
        nuevos = {
            "ultima_calibracion": str(fecha_realizada),
            "proxima_calibracion": str(proxima or ""),
            "certificado_calibracion": equipo.certificado_calibracion.name or "",
        }
        descripcion = (f"Calibración {self.codigo}: última {fecha_realizada:%d/%m/%Y}"
                       + (f", próxima {proxima:%d/%m/%Y}" if proxima else ", sin próxima programada")
                       + (", con certificado." if self.informe else ", sin certificado adjunto."))
        EventoCicloVidaEquipo.objects.get_or_create(
            mantenimiento=self,
            tipo="calibracion",
            defaults={"equipo": equipo, "unidad": self.unidad, "usuario": self.responsable,
                      "descripcion": descripcion},
        )
        if self.unidad_id:
            # Mismo formato que registrar_auditoria, sin que el modelo dependa de la
            # capa de presentación: se resuelve el modelo de auditoría por la aplicación.
            from django.apps import apps

            apps.get_model("formacion", "RegistroAuditoriaUnidad").objects.create(
                unidad=self.unidad, usuario=self.responsable, accion="actualizar",
                entidad=equipo._meta.label, objeto_id=str(equipo.pk),
                descripcion=f"{equipo.codigo_unidad} · {descripcion}"[:255],
                datos_anteriores=anteriores, datos_nuevos=nuevos,
            )

    @property
    def ventana_de_intervencion(self):
        """(fecha, hora de inicio, hora de fin) que ocupa el equipo, en hora local.

        Mientras se programa manda la duración prevista; una vez ejecutada, lo
        que realmente duró, que es lo que corresponde dejar en el calendario.
        """
        if not self.fecha_programada:
            return None
        inicio = timezone.localtime(self.fecha_inicio or self.fecha_programada)
        fin = timezone.localtime(self.fecha_fin) if self.fecha_fin else None
        if not fin or fin <= inicio or fin.date() != inicio.date():
            fin = inicio + timedelta(hours=max(self.duracion_horas or 1, 1))
        if fin.date() != inicio.date():
            fin = inicio.replace(hour=23, minute=59)
        return inicio.date(), inicio.time(), fin.time()

    def sincronizar_bloqueo_de_agenda(self):
        """Refleja la intervención en la agenda: el equipo no se reserva mientras dura.

        Un mantenimiento que no cierra sus horas termina chocando con una
        reserva ya aceptada. El bloqueo es el mismo mecanismo que usa la
        unidad para cualquier cierre, así que aparece en el calendario y lo
        respetan la reserva pública y la validación de conflictos.
        """
        from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad

        bloqueo = BloqueoAgendaUnidad.objects.filter(mantenimiento=self).first()
        ventana = self.ventana_de_intervencion
        procede = bool(
            self.bloquea_agenda and ventana and self.unidad_id
            and self.estado != "cancelado"
        )
        if not procede:
            if bloqueo:
                bloqueo.delete()
            return None
        dia, desde, hasta = ventana
        if bloqueo is None:
            bloqueo = BloqueoAgendaUnidad(unidad_id=self.unidad_id, mantenimiento=self)
        bloqueo.unidad_id = self.unidad_id
        bloqueo.tipo = "mantenimiento"
        bloqueo.titulo = f"{self.codigo} · {self.titulo}"[:160]
        bloqueo.motivo = self.descripcion or self.get_tipo_display()
        bloqueo.fecha_inicio = bloqueo.fecha_fin = dia
        bloqueo.dia_completo = False
        bloqueo.hora_inicio, bloqueo.hora_fin = desde, hasta
        bloqueo.alcance = "equipos"
        bloqueo.bloquea_recursos = True
        bloqueo.bloquea_servicios = True
        bloqueo.visible_en_agenda = True
        bloqueo.activo = self.estado != "completado" or dia >= timezone.localdate()
        bloqueo.save()
        bloqueo.equipos.set([self.equipo_id])
        return bloqueo


class EventoCicloVidaEquipo(models.Model):
    TIPOS = [
        ("registro", "Registro inicial"),
        ("asignacion", "Asignación"),
        ("transferencia", "Transferencia"),
        ("cambio_estado", "Cambio de estado"),
        ("puesta_servicio", "Puesta en servicio"),
        ("incidencia", "Incidencia reportada"),
        ("incidencia_resuelta", "Incidencia resuelta"),
        ("mantenimiento", "Mantenimiento completado"),
        ("calibracion", "Calibración"),
        ("actualizacion", "Actualización"),
        ("baja", "Baja"),
        ("disposicion", "Disposición final"),
        ("cambio_area", "Cambio de área"),
        ("cambio_custodio", "Cambio de custodio"),
        ("cambio_codigo", "Cambio o asignación de código"),
        ("prestamo", "Préstamo"),
        ("devolucion", "Devolución"),
        ("verificacion", "Verificación de existencia"),
        ("diagnostico", "Diagnóstico y decisión técnica"),
    ]

    equipo = models.ForeignKey(
        UnidadEquipo,
        on_delete=models.PROTECT,
        related_name="eventos_ciclo_vida",
    )
    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_equipos",
    )
    tipo = models.CharField(max_length=25, choices=TIPOS)
    fecha = models.DateTimeField(default=timezone.now)
    descripcion = models.TextField()
    estado_anterior = models.CharField(max_length=30, blank=True)
    estado_nuevo = models.CharField(max_length=30, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_ciclo_vida_equipos",
    )
    incidencia = models.ForeignKey(
        IncidenciaEquipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_ciclo_vida",
    )
    mantenimiento = models.ForeignKey(
        MantenimientoEquipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_ciclo_vida",
    )
    evidencia = models.FileField(upload_to="equipos/ciclo_vida/", blank=True)

    class Meta:
        db_table = 'webcitt_eventociclovidaequipo'
        ordering = ["-fecha", "-pk"]
        verbose_name = "Evento del ciclo de vida"
        verbose_name_plural = "Eventos del ciclo de vida"
        constraints = [
            models.UniqueConstraint(
                fields=["incidencia", "tipo"],
                name="evento_unico_por_incidencia_tipo",
                condition=~models.Q(tipo="diagnostico"),
            ),
            models.UniqueConstraint(
                fields=["mantenimiento", "tipo"],
                name="evento_unico_por_mantenimiento_tipo",
            ),
        ]

    def __str__(self):
        return f"{self.equipo.codigo_unidad} · {self.get_tipo_display()}"

    def save(self, *args, **kwargs):
        if not self.unidad_id:
            self.unidad = self.equipo.laboratorio
        self.full_clean()
        super().save(*args, **kwargs)


class RepuestoMantenimiento(models.Model):
    """Lo que se cambió o consumió en una orden de mantenimiento.

    Un repuesto puede salir del inventario de la unidad (y entonces apunta al
    consumible, que descuenta existencias por su propio flujo), comprarse para
    la ocasión o llegar por garantía. Registrarlo aquí es lo que permite saber
    cuánto cuesta sostener cada equipo.
    """

    PROCEDENCIAS = [
        ("inventario", "Del inventario de la unidad"),
        ("compra", "Compra para esta orden"),
        ("garantia", "Cubierto por garantía"),
        ("proveedor", "Aportado por el proveedor del servicio"),
    ]

    mantenimiento = models.ForeignKey(
        MantenimientoEquipo,
        on_delete=models.CASCADE,
        related_name="repuestos",
    )
    consumible = models.ForeignKey(
        'recursos.Consumible',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="repuestos_mantenimiento",
        help_text="Cuando el repuesto sale del inventario de la unidad.",
    )
    pieza = models.ForeignKey(
        'recursos.PiezaEquipo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cambios",
        help_text="La pieza del equipo que se reemplazó, cuando corresponde.",
    )
    descripcion = models.CharField(max_length=200)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    procedencia = models.CharField(max_length=12, choices=PROCEDENCIAS, default="compra")
    observacion = models.CharField(max_length=200, blank=True)
    referencia_adquisicion = models.CharField(max_length=250, blank=True, help_text='Factura, salida de inventario, garantía o expediente que respalda esta pieza; la financiación y revisión administrativa se registran por su propio flujo.')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_repuestomantenimiento'
        ordering = ["mantenimiento", "descripcion"]
        verbose_name = "Repuesto utilizado"
        verbose_name_plural = "Repuestos utilizados"

    def __str__(self):
        return f"{self.descripcion} · {self.mantenimiento.codigo}"

    @property
    def costo_total(self):
        return (self.cantidad or 0) * (self.costo_unitario or 0)

    def clean(self):
        errores = {}
        if self.cantidad is not None and (not self.cantidad.is_finite() or self.cantidad <= 0):
            errores['cantidad'] = 'Registra una cantidad positiva y finita.'
        if self.costo_unitario is not None and (not self.costo_unitario.is_finite() or self.costo_unitario < 0):
            errores['costo_unitario'] = 'Registra un costo no negativo y finito.'
        if self.pieza_id and self.mantenimiento_id and self.pieza.equipo_id != self.mantenimiento.equipo.equipo_id:
            errores['pieza'] = 'La pieza o accesorio debe corresponder al modelo del equipo intervenido.'
        if self.consumible_id and self.mantenimiento_id and self.consumible.unidad_id != self.mantenimiento.unidad_id:
            errores['consumible'] = 'El consumible debe pertenecer a la unidad de la orden.'
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            anterior = type(self).objects.filter(pk=self.pk).values('descripcion', 'cantidad', 'costo_unitario', 'procedencia', 'pieza_id', 'consumible_id', 'referencia_adquisicion', 'observacion').first() if self.pk else None
            self.full_clean()
            resultado = super().save(*args, **kwargs)
            if not anterior or any(str(valor or '') != str(getattr(self, campo) or '') for campo, valor in anterior.items()):
                EventoCicloVidaEquipo.objects.create(
                    equipo=self.mantenimiento.equipo, unidad=self.mantenimiento.unidad,
                    usuario=getattr(self, '_usuario_trazabilidad', None) or self.mantenimiento.responsable,
                    tipo='actualizacion',
                    descripcion=f'Repuesto registrado en {self.mantenimiento.codigo}: {self.descripcion}; cantidad {self.cantidad}; costo unitario USD {self.costo_unitario}; procedencia {self.get_procedencia_display()}; respaldo {self.referencia_adquisicion or "pendiente"}. {self.observacion}',
                )
            return resultado


class ServicioReparacionEquipo(models.Model):
    """Capacidad declarada de atención; no presupone cobertura de todo el inventario."""

    nombre = models.CharField(max_length=180)
    activo = models.BooleanField(default=True)
    familias = models.ManyToManyField('recursos.FamiliaEquipo', blank=True, related_name='servicios_reparacion')
    alcance = models.TextField(help_text='Trabajos que realmente puede realizar y exclusiones técnicas.')
    contacto = models.CharField(max_length=200, blank=True)
    capacidad_mensual = models.PositiveIntegerField(null=True, blank=True, help_text='Casos que puede atender por mes; vacío si aún no se conoce.')
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nombre', 'pk']
        verbose_name = 'Servicio interno de reparación'
        verbose_name_plural = 'Servicios internos de reparación'

    def __str__(self):
        return self.nombre


class DiagnosticoIncidenciaEquipo(models.Model):
    """Decisión técnica trazable antes de reparar, comprar una pieza o sustituir el activo."""

    RUTAS = [('pendiente', 'Por definir'), ('garantia', 'Consultar garantía del proveedor'), ('centro', 'Servicio interno configurado'), ('unidad', 'Personal competente de la unidad'), ('externo', 'Servicio especializado externo')]
    GARANTIAS = [('pendiente', 'Por revisar'), ('cubre', 'Cobertura confirmada'), ('no_cubre', 'No cubre la falla'), ('vencida', 'Vencida'), ('sin_datos', 'Sin documentación disponible')]
    DECISIONES = [('evaluar', 'Completar diagnóstico'), ('reparar', 'Reparar el equipo'), ('repuesto', 'Cambiar pieza o accesorio'), ('reemplazar', 'Proponer reposición del equipo completo'), ('retirar', 'Proponer retiro técnico')]
    FUENTES = [('pendiente', 'Por confirmar'), ('institucional', 'Presupuesto institucional'), ('autogestion', 'Recursos de autogestión'), ('garantia', 'Garantía confirmada'), ('inventario', 'Existencias disponibles'), ('donacion', 'Donación documentada')]
    COMPRAS = [('pendiente', 'Revisión administrativa pendiente'), ('no_requiere', 'No requiere adquisición'), ('revisado', 'Procedimiento revisado por el área competente')]

    incidencia = models.OneToOneField(IncidenciaEquipo, on_delete=models.PROTECT, related_name='diagnostico_tecnico')
    fecha_evaluacion = models.DateField(default=timezone.localdate)
    evaluada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='diagnosticos_equipos')
    causa = models.TextField(help_text='Hallazgos y posible causa; una avería no acredita obsolescencia.')
    impacto = models.TextField(help_text='Seguridad, actividades afectadas, alternativas y urgencia de atención.')
    garantia_revision = models.CharField(max_length=15, choices=GARANTIAS, default='pendiente')
    garantia_respaldo = models.TextField(blank=True, help_text='Consulta, cobertura o exclusión confirmada y referencia del proveedor.')
    pieza = models.ForeignKey('recursos.PiezaEquipo', null=True, blank=True, on_delete=models.SET_NULL, related_name='diagnosticos')
    componente = models.CharField(max_length=180, blank=True, help_text='Nombre de la pieza o accesorio cuando aún no consta en el catálogo.')
    cantidad_componente = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    especificacion_componente = models.TextField(blank=True, help_text='Compatibilidad, modelo y características del repuesto.')
    ruta = models.CharField(max_length=12, choices=RUTAS, default='pendiente')
    servicio = models.ForeignKey(ServicioReparacionEquipo, null=True, blank=True, on_delete=models.PROTECT, related_name='diagnosticos')
    proveedor_externo = models.CharField(max_length=200, blank=True)
    fecha_derivacion = models.DateField(null=True, blank=True)
    respuesta_prevista = models.DateField(null=True, blank=True)
    respuesta = models.TextField(blank=True)
    costo_estimado = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    plazo_estimado_dias = models.PositiveIntegerField(null=True, blank=True)
    decision = models.CharField(max_length=12, choices=DECISIONES, default='evaluar')
    justificacion_decision = models.TextField(blank=True, help_text='Compare reparación, garantía, repuesto y reposición según seguridad, costo, plazo y continuidad.')
    fuente_financiamiento = models.CharField(max_length=15, choices=FUENTES, default='pendiente')
    revision_adquisicion = models.CharField(max_length=15, choices=COMPRAS, default='pendiente')
    autorizacion_referencia = models.CharField(max_length=250, blank=True, help_text='Área competente, autorización y expediente. Autogestión no sustituye el procedimiento de adquisición.')
    evidencia = models.FileField(upload_to='equipos/diagnosticos/', blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_evaluacion', '-pk']
        verbose_name = 'Diagnóstico y decisión de equipo'
        verbose_name_plural = 'Diagnósticos y decisiones de equipos'

    def __str__(self):
        return f'{self.incidencia.equipo.codigo_unidad} · {self.get_decision_display()}'

    @property
    def equipo(self):
        return self.incidencia.equipo

    def clean(self):
        errores = {}
        hoy = timezone.localdate()
        if self.fecha_evaluacion and self.fecha_evaluacion > hoy:
            errores['fecha_evaluacion'] = 'Registra la evaluación realizada, sin fechas futuras.'
        if self.cantidad_componente is not None and (not self.cantidad_componente.is_finite() or self.cantidad_componente <= 0):
            errores['cantidad_componente'] = 'Registra una cantidad positiva y finita.'
        if self.costo_estimado is not None and (not self.costo_estimado.is_finite() or self.costo_estimado < 0):
            errores['costo_estimado'] = 'El costo estimado debe ser finito y no negativo.'
        if not self.incidencia_id:
            return
        equipo = self.equipo
        if self.pieza_id and self.pieza.equipo_id != equipo.equipo_id:
            errores['pieza'] = 'Selecciona una pieza del modelo de este equipo.'
        if self.ruta == 'centro':
            if not self.servicio_id or not self.servicio.activo:
                errores['servicio'] = 'Selecciona un servicio interno activo con cobertura confirmada.'
            elif not equipo.equipo.familia_id or not self.servicio.familias.filter(pk=equipo.equipo.familia_id).exists():
                errores['servicio'] = 'Este servicio no tiene declarada cobertura para la familia del equipo; deriva a revisión especializada.'
        elif self.servicio_id:
            errores['servicio'] = 'El servicio interno solo corresponde a la ruta de atención interna configurada.'
        if self.ruta == 'externo' and not self.proveedor_externo.strip():
            errores['proveedor_externo'] = 'Identifica el servicio especializado o la entidad a consultar.'
        if self.fecha_derivacion and self.fecha_derivacion > hoy:
            errores['fecha_derivacion'] = 'La derivación debe haberse realizado.'
        if self.fecha_derivacion and self.respuesta_prevista and self.respuesta_prevista < self.fecha_derivacion:
            errores['respuesta_prevista'] = 'La respuesta prevista no puede ser anterior a la derivación.'
        if self.decision != 'evaluar':
            if not self.justificacion_decision.strip():
                errores['justificacion_decision'] = 'Justifica la reparación, el repuesto o la reposición antes de proponerla.'
            if self.garantia_revision == 'pendiente':
                errores['garantia_revision'] = 'Revisa primero la garantía; la vigencia no implica cobertura automática.'
            if not self.garantia_respaldo.strip():
                errores['garantia_respaldo'] = 'Deja constancia de la revisión de garantía, incluso si no hay documentación disponible.'
        if self.decision == 'repuesto':
            if not (self.pieza_id or self.componente.strip()):
                errores['componente'] = 'Identifica la pieza o accesorio; no propongas sustituir todo el equipo por defecto.'
            if self.cantidad_componente is None:
                errores['cantidad_componente'] = 'Indica cuántas piezas o accesorios se requieren.'
            if not self.especificacion_componente.strip():
                errores['especificacion_componente'] = 'Describe la compatibilidad o especificación del repuesto.'
        if self.garantia_revision == 'cubre' and self.ruta != 'garantia' and not self.respuesta.strip():
            errores['respuesta'] = 'Explica por qué no se utiliza la garantía cuya cobertura está confirmada.'
        if self.revision_adquisicion == 'revisado' and not self.autorizacion_referencia.strip():
            errores['autorizacion_referencia'] = 'Registra la revisión administrativa y su expediente o autorización.'
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            IncidenciaEquipo.objects.select_for_update().get(pk=self.incidencia_id)
            anterior = type(self).objects.filter(pk=self.pk).values().first() if self.pk else None
            self.full_clean()
            super().save(*args, **kwargs)
            campos = [f for f in self._meta.concrete_fields if f.name not in {'id', 'actualizado_en'}]
            cambio = not anterior or any(str(anterior.get(f.attname) or '') != str(getattr(self, f.attname) or '') for f in campos)
            if cambio:
                detalle = '\n'.join(f'{f.verbose_name}: {getattr(self, f.name)}' for f in campos if f.name not in {'incidencia', 'evaluada_por'} and getattr(self, f.attname) not in (None, ''))
                EventoCicloVidaEquipo.objects.create(equipo=self.equipo, unidad=self.incidencia.unidad, incidencia=self.incidencia, tipo='diagnostico', usuario=self.evaluada_por, descripcion=detalle)
