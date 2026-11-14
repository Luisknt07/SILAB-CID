import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('recursos', '0002_seguimiento_alertas_uso'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='PoliticaUsoEquipo', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('dias_sin_uso', models.PositiveIntegerField(blank=True, null=True,
                validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(36500)],
                verbose_name='Días sin uso acreditado', help_text='Plazo para revisar un activo sin uso acreditado. Vacío: regla no configurada.')),
            ('horas_minimas_anuales', models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2,
                validators=[django.core.validators.MinValueValidator(0)], verbose_name='Mínimo de horas acreditadas en 12 meses',
                help_text='Umbral de atención para revisar poco uso; no acredita por sí solo incumplimiento. Vacío: regla no configurada.')),
            ('dias_atencion', models.PositiveIntegerField(blank=True, null=True,
                validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(36500)],
                verbose_name='Días para atender la alerta después de comunicarla',
                help_text='Se propone al registrar una comunicación real; Dirección puede acordar otra fecha por alerta.')),
            ('fundamento', models.TextField(blank=True, verbose_name='Fundamento de la política')),
            ('actualizada', models.DateTimeField(auto_now=True)),
            ('actualizada_por', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='+', to=settings.AUTH_USER_MODEL)),
        ], options=dict(db_table='webcitt_politicausoequipo', verbose_name='Política de seguimiento del uso de equipos',
            verbose_name_plural='Política de seguimiento del uso de equipos',
            constraints=[models.CheckConstraint(condition=models.Q(('pk', 1)), name='politica_uso_equipo_unica')])),
        migrations.AlterField(model_name='alertausoequipo', name='motivo', field=models.CharField(max_length=20,
            choices=[('sin_uso', 'Sin uso acreditado en el plazo definido'),
                     ('sin_registros', 'Sin uso acreditado; revisar registros'),
                     ('pendiente', 'Cierres de uso por completar'),
                     ('poco_uso', 'Uso acreditado inferior al umbral configurado')])),
    ]
