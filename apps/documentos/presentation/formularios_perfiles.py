"""Campos de evidencia para vincular los resultados al registro operativo de cada perfil."""
from django import forms
from .medicion_perfiles import usa_contrato_perfil


def campos_perfil(unidad, tipo, inicio, fin):
    if not usa_contrato_perfil(unidad, tipo):
        return {}
    campos = {c: forms.CharField(required=False, max_length=3000, label=etiqueta,
                widget=forms.Textarea(attrs={'rows': 2})) for c, etiqueta in (
                    ('objetivo', 'Objetivo de la actividad'), ('metodo', 'Método y comprobaciones realizadas'),
                    ('resultado', 'Resultado comprobado y limitaciones'))}
    def elegir(queryset, etiqueta, multiple=False):
        cls = forms.ModelMultipleChoiceField if multiple else forms.ModelChoiceField
        return cls(queryset=queryset, required=False, label=etiqueta)
    if tipo == 'BOLETINES':
        from apps.observatorios.operacion.models.observatorios import PublicacionObservatorio, IndicadorObservatorio, ValorIndicador
        campos.update(subtipo=forms.ChoiceField(choices=(('publicacion', 'Publicación analítica'),
            ('datos', 'Actualización de una serie de datos'))),
            publicacion_id=elegir(PublicacionObservatorio.objects.filter(unidad=unidad), 'Publicación de origen'),
            indicador_id=elegir(IndicadorObservatorio.objects.filter(unidad=unidad), 'Serie de datos'),
            valores_ids=elegir(ValorIndicador.objects.filter(indicador__unidad=unidad,
                registrado__date__lte=fin).select_related('indicador'), 'Datos incorporados en esta actualización', True))
    elif tipo == 'EVENTOS':
        campos.update(subtipo=forms.ChoiceField(choices=(('socializacion', 'Socialización de resultados'),)),
            beneficiario=forms.CharField(required=False, max_length=300, label='Destinatarios'),
            participantes=forms.IntegerField(required=False, min_value=1, label='Participantes comprobados'),
            fecha_evento=forms.DateField(required=False, label='Fecha de la socialización',
                widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')),
            referencia_acta=forms.CharField(required=False, max_length=300, label='Referencia del acta o lista de asistencia'))
    elif tipo == 'ENSAYOS':
        from apps.centros_experimentales.operacion.models.centros import CicloProductivo, RegistroProduccion
        campos.update(subtipo=forms.ChoiceField(choices=(('ensayo', 'Ensayo con seguimiento del período'),)),
            ciclo_id=elegir(CicloProductivo.objects.filter(eje__unidad=unidad), 'Ciclo y parcela o área'),
            registros_ids=elegir(RegistroProduccion.objects.filter(ciclo__eje__unidad=unidad,
                fecha__range=(inicio, fin)).select_related('ciclo'), 'Seguimientos y mediciones del semestre', True))
    elif tipo == 'PRODUCCION':
        from apps.plantas_piloto.operacion.models.produccion import OrdenProduccion
        from apps.plantas_piloto.operacion.models.calidad import ControlCalidad
        campos.update(subtipo=forms.ChoiceField(choices=(('produccion', 'Orden de producción terminada'),
            ('control_calidad', 'Control de calidad con mediciones'), ('sin_produccion', 'Sin producción finalizada: justificación documentada'))),
            orden_id=elegir(OrdenProduccion.objects.filter(unidad=unidad, demostrativa=False), 'Orden de producción'),
            control_id=elegir(ControlCalidad.objects.filter(unidad=unidad).select_related('plan'), 'Control y mediciones de calidad'),
            periodo_desde=forms.DateField(required=False, initial=inicio, label='Inicio del tramo sin producción',
                widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')),
            periodo_hasta=forms.DateField(required=False, label='Fin del tramo sin producción',
                widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')),
            justificacion_sin_produccion=forms.CharField(required=False, max_length=3000,
                label='Justificación comprobada de la ausencia de producción', widget=forms.Textarea(attrs={'rows': 2})))
    return campos


def detalle_perfil(datos, campos):
    detalle = {}
    for clave in campos:
        valor = datos.get(clave)
        if isinstance(campos[clave], forms.ModelMultipleChoiceField):
            detalle[clave] = sorted(obj.pk for obj in valor) if valor is not None else []
        elif hasattr(valor, 'pk'):
            detalle[clave] = valor.pk
        elif hasattr(valor, 'isoformat'):
            detalle[clave] = valor.isoformat()
        else:
            detalle[clave] = '' if valor is None else valor
    return detalle
