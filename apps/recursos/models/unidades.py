from datetime import date

from django.conf import settings
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.equipos import EquiposServicios


class UnidadEquipoQuerySet(models.QuerySet):
    def publicos(self):
        """Lo que ve el público: activo, en servicio y, si la institución lo exige, con su existencia verificada."""
        consulta = self.filter(activa=True, fecha_baja__isnull=True,
                               estado_unidad__in=UnidadEquipo.ESTADOS_PUBLICOS)
        if getattr(settings, 'CITT_EXIGIR_EQUIPOS_VERIFICADOS', False):
            consulta = consulta.filter(existencia_verificada=True)
        return consulta


class UnidadEquipo(models.Model):
    """Modelo para unidades individuales de equipos"""
    
    ESTADO_UNIDAD_CHOICES = [
        ('disponible', 'Disponible'),
        ('en_uso', 'En Uso'),
        ('mantenimiento', 'En Mantenimiento'),
        ('dañado', 'Dañado'),
        ('prestado', 'Prestado'),
        ('no_disponible', 'No Disponible'),
        ('obsoleto', 'Obsoleto'),
        ('no_localizado', 'No localizado'),
    ]
    # Lo que está bien y en uso: lo único que ve el público. Lo demás solo lo ve quien gestiona.
    ESTADOS_PUBLICOS = ('disponible', 'en_uso', 'prestado')

    objects = UnidadEquipoQuerySet.as_manager()

    CRITICIDAD_CHOICES = [
        ('critico', 'Crítico: su parada detiene el servicio'),
        ('importante', 'Importante: afecta parte de la operación'),
        ('normal', 'Normal: de apoyo o reemplazable'),
    ]

    MOTIVOS_BAJA = [
        ('obsolescencia', 'Obsolescencia técnica'),
        ('vida_util', 'Fin de vida útil'),
        ('dano_irreparable', 'Daño irreparable'),
        ('perdida', 'Pérdida o robo'),
        ('transferencia', 'Transferencia a otra institución'),
        ('otro', 'Otro motivo documentado'),
    ]

    ORIGEN_ADQUISICION_CHOICES = [
        ('asignacion_institucional', 'Asignación institucional'),
        ('compra_publica', 'Compra pública'),
        ('proyecto', 'Proyecto de investigación o vinculación'),
        ('donacion', 'Donación'),
        ('transferencia', 'Transferencia entre unidades'),
        ('prestamo', 'Préstamo o comodato'),
        ('otro', 'Otro origen documentado'),
    ]
    
    # Identificación de la unidad
    codigo_unidad = models.CharField(
        max_length=50,
        unique=True,
        help_text="Código único de la unidad (ej: CNC001, IMP3D002)"
    )
    
    # RELACIÓN CON EQUIPO BASE (sin ubicacion_actual, removido)
    equipo = models.ForeignKey(
        EquiposServicios,
        on_delete=models.CASCADE,
        related_name='unidades',
        help_text="Equipo al que pertenece esta unidad"
    )
    
    # Relación principal con un solo laboratorio
    laboratorio = models.ForeignKey(
        Unidad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='unidades_equipo_principal',
        verbose_name="Laboratorio Primario",
        help_text="Laboratorio principal donde se encuentra esta unidad"
    )

    # CAMBIO: Relación con múltiples laboratorios
    laboratorios = models.ManyToManyField(
        Unidad, db_table='webcitt_unidadequipo_laboratorios',
        blank=True,
        related_name='unidades_equipos',
        verbose_name="Unidades asociadas",
        help_text="Laboratorios asociados donde también puede estar esta unidad"
    )
    
    # Estado de la unidad individual
    estado_unidad = models.CharField(
        max_length=20,
        choices=ESTADO_UNIDAD_CHOICES,
        default='disponible',
        help_text="Estado específico de esta unidad"
    )
    
    # Información específica de la unidad
    numero_serie = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Número de serie del fabricante"
    )

    # Registro patrimonial: lo que la bodega de la Universidad lleva de cada bien.
    TIPOS_BIEN = [
        ('BLD', 'Bien de larga duración (BLD)'),
        ('BCA', 'Bien de control administrativo (BCA)'),
    ]
    codigo_bien = models.CharField(
        'Código del bien',
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        help_text=(
            'Código oficial que asigna la bodega de la Universidad: el número de la etiqueta de código de '
            'barras pegada en el equipo (sin el prefijo institucional). Es único en toda la plataforma.'
        ),
    )
    tipo_bien = models.CharField('Tipo de bien', max_length=3, choices=TIPOS_BIEN, blank=True)
    clase_bien = models.CharField(
        'Clase del bien', max_length=160, blank=True,
        help_text='Grupo y subgrupo de la etiqueta, por ejemplo «Equipo electrónico / Computador de escritorio».',
    )
    custodio = models.CharField(
        'Custodio actual', max_length=160, blank=True,
        help_text='Persona responsable del bien según la bodega. No se muestra al público.',
    )
    ubicacion_bodega = models.CharField('Ubicación según bodega', max_length=160, blank=True)
    color = models.CharField(max_length=60, blank=True)
    material = models.CharField(max_length=80, blank=True)
    dimensiones = models.CharField(max_length=160, blank=True)
    fecha_ingreso_bodega = models.DateField('Fecha de ingreso a bodega', null=True, blank=True)
    valor_contable = models.DecimalField(
        'Valor contable', max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Valor registrado por la bodega. No se muestra al público.',
    )
    version_sistema = models.CharField(
        'Versión del sistema o firmware', max_length=80, blank=True,
        help_text='La versión con la que corre esta unidad (por ejemplo, la del sistema del visor o el firmware de la impresora).')
    sistema_actualizado = models.DateField('Actualizado el', null=True, blank=True)
    # Que el equipo existe de verdad: lo confirma quien gestiona la unidad (o anota que no se localizó).
    existencia_verificada = models.BooleanField('Existencia verificada', default=False, db_index=True)
    existencia_verificada_en = models.DateTimeField('Verificada el', null=True, blank=True)
    existencia_verificada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='equipos_verificados', verbose_name='Verificada por')
    existencia_nota = models.CharField('Nota de la verificación', max_length=240, blank=True)

    origen_adquisicion = models.CharField(
        max_length=30,
        choices=ORIGEN_ADQUISICION_CHOICES,
        default='asignacion_institucional',
        help_text='Indica cómo ingresó esta unidad física al laboratorio.',
    )

    fecha_adquisicion = models.DateField(
        blank=True,
        null=True,
        help_text='Fecha de adquisición, asignación o recepción de esta unidad física.',
    )

    documento_adquisicion = models.CharField(
        max_length=120,
        blank=True,
        help_text='Código de acta, contrato, factura, proyecto o documento de respaldo.',
    )

    valor_referencial = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Valor referencial del activo; no reemplaza el registro contable institucional.',
    )
    
    observaciones = models.TextField(
        blank=True,
        null=True,
        help_text="Observaciones específicas de esta unidad"
    )
    
    # Mantenimiento e insumos
    fecha_ultimo_mantenimiento = models.DateField(
        blank=True,
        null=True,
        help_text="Fecha del último mantenimiento realizado"
    )
    
    proximo_mantenimiento = models.DateField(
        blank=True,
        null=True,
        help_text="Fecha estimada del próximo mantenimiento"
    )
    
    # Ambos se derivan de los insumos compatibles (ConsumiblePorEquipo) de la
    # ficha tecnica en esta unidad; no se editan a mano. El texto que quedo de
    # cargas anteriores sin relacion estructurada se conserva como heredado.
    criticidad = models.CharField(
        'Criticidad',
        max_length=12,
        choices=CRITICIDAD_CHOICES,
        default='normal',
        help_text='Un equipo crítico exige plan de mantenimiento vigente.',
    )

    vida_util_anios = models.PositiveSmallIntegerField(
        'Vida útil (años)',
        default=0,
        help_text='Años de vida útil previstos desde la adquisición. 0: sin vida útil definida.',
    )

    garantia_meses = models.PositiveSmallIntegerField(
        'Garantía (meses)',
        default=0,
        help_text='Meses de garantía desde la adquisición. Con este dato la fecha se calcula sola.',
    )

    garantia_hasta = models.DateField(
        'Garantía hasta',
        null=True,
        blank=True,
        help_text='Mientras esté vigente, el mantenimiento correctivo lo cubre el proveedor.',
    )

    garantia_cobertura = models.TextField(
        'Qué cubre la garantía',
        blank=True,
        help_text='Partes, mano de obra, visitas incluidas y lo que la anula.',
    )

    garantia_contacto = models.CharField(
        'Proveedor o contacto de garantía',
        max_length=200,
        blank=True,
    )

    fecha_baja = models.DateField(
        'Fecha de baja',
        null=True,
        blank=True,
        help_text='Al registrarla, el activo sale de la operación y queda en el historial.',
    )

    motivo_baja = models.CharField(
        'Motivo de la baja',
        max_length=20,
        choices=MOTIVOS_BAJA,
        blank=True,
    )

    observacion_baja = models.TextField(
        'Acta o justificación de la baja',
        blank=True,
        help_text='Número de acta, destino del activo y responsable de la disposición.',
    )

    reemplazado_por = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reemplaza_a',
        help_text='Activo que asume la función del que se da de baja.',
    )

    requiere_insumos = models.BooleanField(
        default=False,
        help_text="Se marca solo cuando el equipo tiene insumos compatibles registrados"
    )

    insumos_necesarios = models.TextField(
        blank=True,
        null=True,
        help_text="Nombres de los insumos compatibles; se actualiza al registrarlos"
    )

    
    ubicacion_especifica = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Ubicación específica dentro del laboratorio (ej: Mesa 3, Estante A2)"
    )
    
    # Metadatos
    fecha_ingreso = models.DateTimeField(
        auto_now_add=True,
        null=True,  # Permitir null para registros existentes
        blank=True,
        help_text="Fecha de ingreso de la unidad al sistema"
    )
    
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        help_text="Última actualización de la información"
    )
    
    activa = models.BooleanField(
        default=True,
        help_text="Si la unidad está activa en el sistema"
    )
    
    class Meta:
        db_table = 'webcitt_unidadequipo'
        ordering = ['equipo__nombre', 'codigo_unidad']
        verbose_name = 'Unidad de Equipo'
        verbose_name_plural = 'Unidades de Equipos'
        indexes = [
            models.Index(fields=['codigo_unidad']),
            models.Index(fields=['estado_unidad']),
            models.Index(fields=['equipo', 'estado_unidad']),
        ]
    
    def __str__(self):
        return f"{self.codigo_unidad} - {self.equipo.nombre}"
    
    @property
    def vida_util_efectiva(self):
        """Años de vida útil del activo; sin valor propio, la referencia de su tipo."""
        return self.vida_util_anios or getattr(self.equipo, 'vida_util_referencia_anios', 0) or 0

    @property
    def vida_util_por_horas(self):
        """Horas de operación que agotan este tipo de equipo; 0 si solo se mide por tiempo."""
        return getattr(self.equipo, 'vida_util_horas', 0) or 0

    @property
    def fin_vida_util(self):
        """Fecha en que se cumple la vida útil prevista, o None si no está definida."""
        anios = self.vida_util_efectiva
        if not anios or not self.fecha_adquisicion:
            return None
        try:
            return self.fecha_adquisicion.replace(year=self.fecha_adquisicion.year + anios)
        except (ValueError, OverflowError):
            if self.fecha_adquisicion.month == 2 and self.fecha_adquisicion.day == 29:
                try:
                    return self.fecha_adquisicion.replace(year=self.fecha_adquisicion.year + anios, day=28)
                except (ValueError, OverflowError):
                    pass
            return None

    def vida_util_consumida(self, hoy=None):
        """Porcentaje de la vida útil ya transcurrido; None si no se puede calcular."""
        fin = self.fin_vida_util
        if fin is None:
            return None
        hoy = hoy or timezone.localdate()
        total = (fin - self.fecha_adquisicion).days or 1
        return max(0, min(200, round(100 * (hoy - self.fecha_adquisicion).days / total)))

    @property
    def dado_de_baja(self):
        return self.fecha_baja is not None

    @property
    def fin_garantia(self):
        """Fecha de fin de garantía: la registrada o la que resulta de los meses."""
        if self.garantia_hasta:
            return self.garantia_hasta
        if self.garantia_meses and self.fecha_adquisicion:
            meses = self.fecha_adquisicion.month - 1 + self.garantia_meses
            return date(
                self.fecha_adquisicion.year + meses // 12,
                meses % 12 + 1,
                min(self.fecha_adquisicion.day, 28),
            )
        return None

    def en_garantia(self, hoy=None):
        fin = self.fin_garantia
        return bool(fin and fin >= (hoy or timezone.localdate()))

    def insumos_compatibles(self):
        """Insumos de esta unidad registrados como compatibles con la ficha tecnica."""
        from apps.recursos.models.consumibles import Consumible

        if not self.equipo_id or not self.laboratorio_id:
            return Consumible.objects.none()
        return Consumible.objects.filter(
            por_equipo__equipo_id=self.equipo_id, unidad_id=self.laboratorio_id,
        ).order_by('nombre')

    def sincronizar_insumos(self):
        """Recalcula el resumen desde la relacion estructurada y lo guarda.

        Se llama cuando cambia la relacion, no al editar el equipo: asi la
        descripcion nunca dice una cosa y la reserva ofrece otra.
        """
        nombres = list(self.insumos_compatibles().values_list('nombre', flat=True))
        self.requiere_insumos = bool(nombres)
        self.insumos_necesarios = ", ".join(nombres)
        UnidadEquipo.objects.filter(pk=self.pk).update(
            requiere_insumos=self.requiere_insumos, insumos_necesarios=self.insumos_necesarios,
        )

    def clean(self):
        super().clean()
        from apps.recursos.models.adquisiciones import validar_habilitacion
        validar_habilitacion(self)
        # Validar código único
        if UnidadEquipo.objects.filter(codigo_unidad=self.codigo_unidad).exclude(pk=self.pk).exists():
            raise ValidationError("Ya existe una unidad con este código.")
        # Un QR o una etiqueta vieja con ese código abriría otro equipo.
        if AliasCodigoUnidadEquipo.objects.filter(codigo=self.codigo_unidad).exclude(unidad_equipo_id=self.pk).exists():
            raise ValidationError({'codigo_unidad': 'Ese código perteneció a otro equipo; elige uno distinto.'})

        # Validar que si requiere insumos, debe especificarlos
        if self.requiere_insumos and not self.insumos_necesarios:
            raise ValidationError("Si requiere insumos, debe especificar cuáles son necesarios.")

        # Validar fechas de mantenimiento
        if (self.fecha_ultimo_mantenimiento and self.proximo_mantenimiento and
            self.proximo_mantenimiento <= self.fecha_ultimo_mantenimiento):
            raise ValidationError("La fecha del próximo mantenimiento debe ser posterior al último mantenimiento.")
        self._validar_retiro_y_sustitucion()

    def _validar_retiro_y_sustitucion(self):
        errores = {}
        anterior = (type(self).objects.filter(pk=self.pk).values(
            'fecha_baja', 'motivo_baja', 'observacion_baja', 'reemplazado_por_id', 'laboratorio_id',
        ).first() if self.pk else None)
        if anterior and anterior['fecha_baja']:
            rectifica = any(anterior[campo] != getattr(self, campo) for campo in (
                'fecha_baja', 'motivo_baja', 'observacion_baja',
            )) or bool(anterior['reemplazado_por_id'] and anterior['reemplazado_por_id'] != self.reemplazado_por_id)
            if rectifica and not str(getattr(self, '_justificacion_ciclo_vida', '') or '').strip():
                errores['observacion_baja'] = 'Explica la rectificación del retiro anterior; su historial se conserva.'
        if self.fecha_baja:
            if self.fecha_baja > timezone.localdate():
                errores['fecha_baja'] = 'Registra la fecha real de retiro; una baja futura pertenece a la planificación.'
            elif self.fecha_adquisicion and self.fecha_baja < self.fecha_adquisicion:
                errores['fecha_baja'] = 'El retiro no puede ser anterior a la adquisición del activo.'
            if not self.motivo_baja:
                errores['motivo_baja'] = 'Indica el motivo técnico del retiro de operación.'
            if not str(self.observacion_baja or '').strip():
                errores['observacion_baja'] = 'Documenta la justificación, referencia de respaldo y destino previsto.'
        elif self.motivo_baja or self.observacion_baja or self.reemplazado_por_id:
            errores['fecha_baja'] = 'Registra el retiro operativo para vincular su motivo, respaldo o sustitución.'
        if self.reemplazado_por_id:
            nueva_relacion = (not anterior or anterior['reemplazado_por_id'] != self.reemplazado_por_id
                              or anterior['laboratorio_id'] != self.laboratorio_id)
            if self.pk == self.reemplazado_por_id:
                errores['reemplazado_por'] = 'Un activo no puede sustituirse a sí mismo.'
            else:
                sustituto = type(self).objects.filter(pk=self.reemplazado_por_id).first()
                if sustituto is None:
                    errores['reemplazado_por'] = 'El activo sustituto ya no existe.'
                elif nueva_relacion and (not self.laboratorio_id or sustituto.laboratorio_id != self.laboratorio_id):
                    errores['reemplazado_por'] = 'El sustituto debe pertenecer a la misma unidad principal.'
                elif nueva_relacion and (not sustituto.activa or sustituto.fecha_baja
                        or sustituto.estado_unidad not in ('disponible', 'en_uso')):
                    errores['reemplazado_por'] = 'El sustituto debe estar activo y operativo en la unidad.'
                enlaces = dict(type(self).objects.filter(reemplazado_por__isnull=False).values_list(
                    'pk', 'reemplazado_por_id'))
                vistos = {self.pk} if self.pk else set()
                siguiente = self.reemplazado_por_id
                while siguiente is not None:
                    if siguiente in vistos:
                        errores['reemplazado_por'] = 'La sustitución crearía o conservaría un ciclo entre activos.'
                        break
                    vistos.add(siguiente)
                    siguiente = enlaces.get(siguiente)
        if errores:
            raise ValidationError(errores)

    @property
    def completitud_ficha(self):
        """Porcentaje conjunto de identificación y levantamiento técnico."""
        valores = (
            self.codigo_unidad,
            self.equipo.nombre,
            self.equipo.descripcion,
            self.equipo.caracteristicas_publicas,
            self.equipo.uso_publico,
            self.equipo.instrucciones_publicas,
            self.equipo.marca,
            self.equipo.modelo,
            self.numero_serie,
            self.ubicacion_especifica,
            self.fecha_adquisicion or self.equipo.fecha_adquisicion,
            self.documento_adquisicion,
            self.equipo.ficha_tecnica or self.equipo.manual_operacion,
        )
        identificacion = sum(bool(valor) for valor in valores) * 100 / len(valores)
        return round((identificacion + self.equipo.completitud_tecnica) / 2)


    @property
    def codigo_etiqueta(self):
        """Lo que dice la etiqueta: el código oficial con el prefijo institucional o, sin él, el del sistema."""
        from apps.recursos.models.identificadores import PREFIJO_INSTITUCIONAL

        return f'{PREFIJO_INSTITUCIONAL}-{self.codigo_bien}' if self.codigo_bien else self.codigo_unidad

    def save(self, *args, **kwargs):
        from apps.recursos.models.identificadores import limpiar_codigo_bien
        # Un código vacío no ocupa el lugar único; uno leído con prefijo se guarda sin él.
        self.codigo_bien = limpiar_codigo_bien(self.codigo_bien) or None
        with transaction.atomic():
            if (self.fecha_baja or self.reemplazado_por_id) and self.laboratorio_id:
                # El mismo bloqueo serializa sustituciones concurrentes de la unidad.
                Unidad.objects.select_for_update().get(pk=self.laboratorio_id)
                if self.reemplazado_por_id:
                    # Un traslado o cambio operativo del sustituto espera a la decisión.
                    list(type(self).objects.select_for_update().filter(pk=self.reemplazado_por_id).values_list('pk', flat=True))
            if self.fecha_baja:
                self.activa = False
                self.estado_unidad = 'no_disponible'
                if kwargs.get('update_fields') is not None:
                    kwargs['update_fields'] = set(kwargs['update_fields']) | {'activa', 'estado_unidad'}
            self.full_clean()
            super().save(*args, **kwargs)
    
    # PROPIEDADES DE ESTADO
    
    @property
    def disponible_para_reserva(self):
        """
        Indica si la unidad está disponible para reserva en este momento,
        considerando el estado físico y reservas confirmadas/en proceso.
        """
        if self.fecha_baja or self.estado_unidad != 'disponible' or not self.activa:
            return False

        # Verificar si existe una reserva confirmada/en proceso para hoy y este horario
        from datetime import date, datetime
        from apps.reservas.models.reservas import Reserva

        hoy = date.today()
        ahora = datetime.now().time()

        # Buscar reservas que solapen con el horario actual
        reservas_conflicto = Reserva.objects.filter(
            unidades_seleccionadas__contains=self.codigo_unidad,
            fecha=hoy,
            estado__in=['confirmada', 'en_proceso']
        ).filter(
            models.Q(hora_inicio__lte=ahora, hora_fin__gt=ahora)
        )

        return not reservas_conflicto.exists()

    @property
    def es_publico(self):
        """La misma regla que UnidadEquipoQuerySet.publicos, para un equipo ya cargado."""
        return (not self.fecha_baja and self.activa and self.estado_unidad in self.ESTADOS_PUBLICOS
                and (self.existencia_verificada or not getattr(settings, 'CITT_EXIGIR_EQUIPOS_VERIFICADOS', False)))

    @property
    def espacios_asociados_ids_csv(self):
        """Identificadores de las áreas donde esta unidad puede utilizarse."""
        return ','.join(str(espacio.pk) for espacio in self.espacios_asociados.all())
    
    @property
    def en_mantenimiento_preventivo(self):
        """Verifica si está próxima a mantenimiento"""
        if not self.proximo_mantenimiento:
            return False
        
        from datetime import date, timedelta
        fecha_limite = date.today() + timedelta(days=7)  # Una semana de anticipación
        return self.proximo_mantenimiento <= fecha_limite
    
    @property
    def requiere_atencion(self):
        """Indica si la unidad requiere atención (mantenimiento, insumos, etc.)"""
        return (
            self.requiere_insumos or 
            self.en_mantenimiento_preventivo or 
            self.estado_unidad in ['mantenimiento', 'dañado']
        )
    
    @property
    def laboratorio_nombre(self):
        """Retorna el nombre del laboratorio principal o 'Sin asignar'"""
        if self.laboratorio:
            return self.laboratorio.nombre
        return 'Sin asignar'

    @property
    def ubicacion_completa(self):
        """Retorna la ubicación completa de la unidad"""
        ubicacion = self.laboratorio_nombre
        if self.ubicacion_especifica:
            ubicacion += f" - {self.ubicacion_especifica}"
        return ubicacion
    
    # MÉTODOS DE DISPONIBILIDAD DINÁMICA
    
    # MÉTODOS DE RESERVA Y GESTIÓN
    
    # MÉTODOS DE MANTENIMIENTO


class AliasCodigoUnidadEquipo(models.Model):
    """Código histórico que conserva los enlaces al cambiar la codificación de un equipo."""

    codigo = models.CharField(max_length=50, unique=True)
    unidad_equipo = models.ForeignKey(
        UnidadEquipo,
        on_delete=models.CASCADE,
        related_name='codigos_anteriores',
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_aliascodigounidadequipo'
        ordering = ('codigo',)
        verbose_name = 'Código anterior de equipo'
        verbose_name_plural = 'Códigos anteriores de equipos'

    def __str__(self):
        return f'{self.codigo} → {self.unidad_equipo.codigo_unidad}'
