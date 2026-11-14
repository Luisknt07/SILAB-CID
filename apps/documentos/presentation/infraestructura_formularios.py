"""Campos del registro directo de planes y ejecuciones de infraestructura."""
from django import forms

from apps.documentos.models.infraestructura import (
    CRITICIDADES_INFRAESTRUCTURA, CLAVES_INFRAESTRUCTURA,
)
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable


class PlanInfraChoice(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        detalle = obj.detalle if isinstance(obj.detalle, dict) else {}
        return f'{obj.codigo} · {detalle.get("ubicacion", "Área sin identificar")} · {obj.titulo}'


def campos_infraestructura(unidad, tipo):
    def fecha(etiqueta, **extra):
        return forms.DateField(required=False, label=etiqueta,
            widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'), **extra)
    if tipo == 'PLAN-INFRA':
        return dict(
            alcance_infraestructura=forms.ChoiceField(required=False, initial='aplica',
                choices=[('aplica', 'Aplica: registrar intervención y cronograma'),
                         ('no_aplica', 'No aplica en el año de la declaración: justificar y respaldar')],
                label='Alcance del mantenimiento de infraestructura'),
            justificacion_alcance=forms.CharField(required=False, max_length=3000,
                label='Justificación del alcance', widget=forms.Textarea(attrs={'rows': 2}),
                help_text='Obligatoria si no aplica. En ese caso deja vacíos el área, la intervención y el calendario.'),
            alcance_todo_laboratorio=forms.BooleanField(required=False,
                label='Confirmo que el plan adjunto cubre todos los espacios e instalaciones de la unidad',
                help_text='Marca sólo si el archivo y su justificación respaldan el alcance completo. Sin marcar, este plan cubre únicamente su espacio registrado.'),
            espacio_id=forms.ModelChoiceField(required=False,
                queryset=EspacioReservable.objects.filter(unidad=unidad, activo=True),
                label='Espacio registrado (cuando corresponda)',
                help_text='Para instalaciones generales, identifica el área en el siguiente campo.'),
            ubicacion=forms.CharField(required=False, max_length=300, label='Espacio, área o instalación a intervenir'),
            intervencion=forms.CharField(required=False, max_length=300, label='Intervención prevista'),
            criticidad=forms.ChoiceField(required=False, label='Criticidad de la intervención',
                choices=[('', 'Selecciona la criticidad')] + list(CRITICIDADES_INFRAESTRUCTURA)),
            fecha_programada=fecha('Primera fecha programada'),
            frecuencia_dias=forms.IntegerField(required=False, min_value=0, max_value=3660,
                initial=0, label='Frecuencia en días', help_text='0: intervención única. Por ejemplo, 30: cada 30 días.'),
            fecha_fin_programacion=fecha('Fin de la programación (opcional)',
                help_text='Si queda vacío, la frecuencia se proyecta hasta el fin del período consultado.'))
    if tipo == 'EJECUCION-INFRA':
        return dict(
            plan_id=PlanInfraChoice(required=False,
                queryset=EvidenciaGestionUnidad.objects.filter(unidad=unidad,
                    tipo='PLAN-INFRA', estado='validado', detalle__alcance_infraestructura='aplica').order_by('codigo'),
                label='Plan de infraestructura verificado',
                help_text='La ubicación y la intervención se toman del plan, conservando su versión y respaldo.'),
            fecha_programada=fecha('Fecha programada que atiende esta intervención',
                help_text='Debe coincidir con una ocurrencia de la frecuencia declarada en el plan.'),
            fecha_inicio=fecha('Inicio real de la intervención'),
            fecha_fin=fecha('Cierre real de la intervención'),
            resultado=forms.CharField(required=False, max_length=3000, label='Resultado comprobado',
                widget=forms.Textarea(attrs={'rows': 3})))
    return {}


def detalle_infraestructura(datos, campos):
    detalle = {}
    for clave in CLAVES_INFRAESTRUCTURA:
        if clave not in campos:
            continue
        valor = datos.get(clave)
        detalle[clave] = valor.pk if hasattr(valor, 'pk') else (
            valor.isoformat() if hasattr(valor, 'isoformat') else None if valor is None else valor)
    return detalle
