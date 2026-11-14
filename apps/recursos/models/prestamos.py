"""Préstamo de equipos: quién lo retira, para qué, y en qué estado vuelve.

Hasta ahora un préstamo solo se veía como la marca «prestado» en el activo:
una casilla sin traza. No decía quién lo tiene, desde cuándo, para qué, cuándo
debe volver ni en qué condición salió, y el expediente exigía ese registro en
un archivo cargado a mano.

Aquí queda el acta viva. Un préstamo **interno** sale a otra área de la
Universidad y basta con el responsable que lo retira; uno **externo** sale de
la institución y exige la institución receptora y la autorización, porque el
activo deja de estar bajo custodia de la unidad. En los dos casos el equipo
queda fuera de reservas mientras está afuera, y el calendario lo muestra.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


def _codigo_prestamo():
    return f"PRE-{uuid.uuid4().hex[:10].upper()}"


class PrestamoEquipo(models.Model):
    """Una salida del equipo con su retorno comprometido."""

    TIPOS = [
        ("interno", "Interno: sale a otra área de la Universidad"),
        ("externo", "Externo: sale de la Universidad"),
    ]
    ESTADOS = [
        ("solicitado", "Solicitado"),
        ("entregado", "Entregado"),
        ("devuelto", "Devuelto"),
        ("no_devuelto", "No devuelto: pérdida declarada"),
        ("cancelado", "Cancelado"),
    ]
    ESTADOS_FUERA = {"entregado"}
    CONDICIONES = [
        ("bueno", "Bueno, sin novedades"),
        ("observado", "Con observaciones"),
        ("danado", "Dañado"),
    ]

    codigo = models.CharField(max_length=20, unique=True, default=_codigo_prestamo, editable=False)
    equipo = models.ForeignKey(
        UnidadEquipo,
        on_delete=models.PROTECT,
        related_name="prestamos",
    )
    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prestamos_equipos",
        editable=False,
    )
    tipo = models.CharField(max_length=10, choices=TIPOS, default="interno")
    estado = models.CharField(max_length=12, choices=ESTADOS, default="solicitado")

    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prestamos_solicitados",
        help_text="Cuando quien retira tiene cuenta en la plataforma.",
    )
    nombre_solicitante = models.CharField(
        "Quién retira",
        max_length=160,
        blank=True,
        help_text="Nombre completo; obligatorio si no tiene cuenta.",
    )
    documento_solicitante = models.CharField("Cédula o documento", max_length=30, blank=True)
    institucion = models.CharField(
        "Institución o área receptora",
        max_length=180,
        blank=True,
        help_text="Obligatoria en el préstamo externo: es quien responde por el activo.",
    )
    contacto = models.CharField("Correo o teléfono", max_length=180, blank=True)
    proposito = models.TextField("Para qué se presta")

    fecha_salida = models.DateTimeField(default=timezone.now)
    fecha_retorno_previsto = models.DateTimeField()
    fecha_retorno_real = models.DateTimeField(null=True, blank=True)

    entregado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prestamos_entregados",
    )
    recibido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prestamos_recibidos",
        help_text="Quién verifica el equipo cuando vuelve.",
    )
    autorizado_por = models.CharField(
        "Autoriza la salida",
        max_length=160,
        blank=True,
        help_text="Obligatorio en el préstamo externo: quién autoriza que el activo salga.",
    )

    condicion_salida = models.CharField(max_length=10, choices=CONDICIONES, default="bueno")
    condicion_retorno = models.CharField(max_length=10, choices=CONDICIONES, blank=True)
    observaciones_salida = models.TextField(blank=True)
    observaciones_retorno = models.TextField(blank=True)
    acta = models.FileField(
        "Acta o autorización",
        upload_to="equipos/prestamos/",
        blank=True,
        help_text="El acta firmada; en el préstamo externo es la evidencia que exige el expediente.",
    )

    estado_equipo_previo = models.CharField(max_length=20, blank=True, editable=False)
    bloquea_agenda = models.BooleanField(
        "Reservar el equipo en el calendario",
        default=True,
        help_text="Cierra esas fechas en la agenda: el equipo está afuera y nadie puede reservarlo.",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_prestamoequipo'
        ordering = ["-fecha_salida", "-pk"]
        verbose_name = "Préstamo de equipo"
        verbose_name_plural = "Préstamos de equipos"
        indexes = [
            models.Index(fields=["estado", "fecha_retorno_previsto"]),
            models.Index(fields=["equipo", "fecha_salida"]),
        ]

    def __str__(self):
        return f"{self.codigo} · {self.equipo.codigo_unidad}"

    @property
    def quien_retira(self):
        if self.solicitante_id:
            return self.solicitante.get_full_name() or self.solicitante.get_username()
        return self.nombre_solicitante or "Sin registrar"

    @property
    def esta_afuera(self):
        return self.estado in self.ESTADOS_FUERA

    @property
    def vencido(self):
        """Debía haber vuelto y no ha vuelto."""
        return bool(
            self.esta_afuera
            and self.fecha_retorno_previsto
            and self.fecha_retorno_previsto < timezone.now()
        )

    @property
    def dias_fuera(self):
        if not self.fecha_salida:
            return 0
        fin = self.fecha_retorno_real or timezone.now()
        return max((fin - self.fecha_salida).days, 0)

    def clean(self):
        errores = {}
        from apps.documentos.models.respaldo_medicion import es_laboratorio, validar_respaldo
        unidad = self.unidad if self.unidad_id else self.equipo.laboratorio if self.equipo_id else None
        laboratorio = bool(unidad and es_laboratorio(unidad))
        anterior = type(self).objects.filter(pk=self.pk).values('estado', 'tipo').first() if self.pk else None
        nueva_salida = self.estado == 'entregado' and (not anterior or anterior['estado'] != 'entregado'
                                                       or anterior['tipo'] != self.tipo)
        if self.fecha_salida and self.fecha_retorno_previsto and (
                self.fecha_retorno_previsto <= self.fecha_salida):
            errores["fecha_retorno_previsto"] = "El retorno tiene que ser posterior a la salida."
        if not self.solicitante_id and not self.nombre_solicitante.strip():
            errores["nombre_solicitante"] = "Registra quién retira el equipo."
        if self.tipo == "externo" and (not laboratorio or nueva_salida):
            # El activo sale de la Universidad: sin receptor ni autorización no
            # hay a quién reclamarlo.
            if not self.institucion.strip():
                errores["institucion"] = "Un préstamo externo exige la institución receptora."
            if not self.autorizado_por.strip():
                errores["autorizado_por"] = "Un préstamo externo exige quién autoriza la salida."
            if laboratorio:
                if not self.entregado_por_id or not self.entregado_por.is_active:
                    errores['entregado_por'] = 'Registra al responsable de la entrega del equipo.'
                if not self.acta:
                    errores['acta'] = 'Antes de entregar un equipo fuera de la Universidad adjunta el acta o autorización firmada.'
                else:
                    try:
                        if getattr(self.acta, '_committed', True):
                            validar_respaldo(self.acta)
                        else:
                            # Validar sin cerrar el archivo aún no guardado; el
                            # formulario y save() comprueban la misma transición.
                            self.acta.open('rb')
                            copia = ContentFile(self.acta.read(25 * 1024 * 1024 + 1), name=self.acta.name)
                            self.acta.seek(0)
                            validar_respaldo(copia)
                    except (ValidationError, OSError, ValueError) as error:
                        errores['acta'] = (error.messages if isinstance(error, ValidationError) else
                            'El acta debe ser un PDF o imagen legible y disponible.')
        if self.estado == "devuelto":
            if not self.fecha_retorno_real:
                errores["fecha_retorno_real"] = "Registra cuándo volvió el equipo."
            if not self.condicion_retorno:
                errores["condicion_retorno"] = "Registra en qué condición volvió."
            if laboratorio and (not self.recibido_por_id or not self.recibido_por.is_active):
                errores['recibido_por'] = 'Registra al responsable que recibió y comprobó el equipo.'
        if self.fecha_retorno_real and self.fecha_salida and self.fecha_retorno_real < self.fecha_salida:
            errores["fecha_retorno_real"] = "El retorno no puede ser anterior a la salida."
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        from apps.recursos.models.mantenimiento import estado_base_operativo, sincronizar_estado_operativo

        if not self.unidad_id:
            self.unidad = self.equipo.laboratorio
        if self.estado == "devuelto" and not self.fecha_retorno_real:
            self.fecha_retorno_real = timezone.now()

        with transaction.atomic():
            equipo = UnidadEquipo.objects.select_for_update().get(pk=self.equipo_id)
            anterior = None
            if self.pk:
                anterior = type(self).objects.select_for_update().filter(pk=self.pk).first()
            estaba_afuera = bool(anterior and anterior.esta_afuera)
            if self.esta_afuera and not estaba_afuera:
                self.estado_equipo_previo = estado_base_operativo(equipo)

            self.full_clean()
            super().save(*args, **kwargs)
            if estaba_afuera or self.esta_afuera:
                sincronizar_estado_operativo(
                    self.equipo_id, self.estado_equipo_previo or "disponible")
            self.sincronizar_bloqueo_de_agenda()

    @property
    def ventana_de_salida(self):
        """(desde, hasta) en fechas locales: lo que el equipo está fuera."""
        if not self.fecha_salida:
            return None
        desde = timezone.localtime(self.fecha_salida).date()
        final = self.fecha_retorno_real or self.fecha_retorno_previsto
        hasta = timezone.localtime(final).date() if final else desde
        return desde, max(hasta, desde)

    def sincronizar_bloqueo_de_agenda(self):
        """El calendario muestra el equipo afuera durante todo el préstamo.

        Un préstamo es una indisponibilidad como cualquier otra: se resuelve
        con el mismo cierre de agenda que usa el mantenimiento, para que la
        reserva choque antes de aceptarse y no el día de la entrega.
        """
        from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad

        bloqueo = BloqueoAgendaUnidad.objects.filter(prestamo=self).first()
        ventana = self.ventana_de_salida
        procede = bool(
            self.bloquea_agenda and ventana and self.unidad_id
            and self.estado in {"solicitado", "entregado", "no_devuelto"}
        )
        if not procede:
            if bloqueo:
                bloqueo.delete()
            return None
        desde, hasta = ventana
        if bloqueo is None:
            bloqueo = BloqueoAgendaUnidad(unidad_id=self.unidad_id, prestamo=self)
        bloqueo.unidad_id = self.unidad_id
        bloqueo.tipo = "prestamo"
        bloqueo.titulo = f"{self.codigo} · {self.equipo.codigo_unidad} prestado"[:160]
        bloqueo.motivo = f"{self.get_tipo_display()}. {self.quien_retira}. {self.proposito}".strip()
        bloqueo.fecha_inicio, bloqueo.fecha_fin = desde, hasta
        bloqueo.dia_completo = True
        bloqueo.hora_inicio = bloqueo.hora_fin = None
        bloqueo.alcance = "equipos"
        bloqueo.bloquea_recursos = True
        bloqueo.bloquea_servicios = True
        bloqueo.visible_en_agenda = True
        bloqueo.activo = True
        bloqueo.save()
        bloqueo.equipos.set([self.equipo_id])
        return bloqueo
