import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('documentos', '0007_verificacion_funcional_equipos'),
                    ('recursos', '0001_propiedad_modelos')]
    operations = [migrations.CreateModel(
        name='ControlAutomaticoDocumento',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('metodo', models.CharField(max_length=80)),
            ('version_documento', models.PositiveSmallIntegerField(default=0)),
            ('sha256', models.CharField(blank=True, max_length=64)),
            ('estado', models.CharField(choices=[('automatico', 'Comprobado automáticamente'),
                ('revision', 'Requiere revisión'), ('bloqueado', 'Bloqueado por inconsistencias'),
                ('sin_archivo', 'Sin archivo')], db_index=True, default='sin_archivo', max_length=12)),
            ('hallazgos', models.JSONField(blank=True, default=list)),
            ('resumen', models.JSONField(blank=True, default=dict)),
            ('fuentes_sha256', models.CharField(blank=True, max_length=64)),
            ('comprobado_en', models.DateTimeField(default=django.utils.timezone.now)),
            ('aplicado', models.BooleanField(default=False)),
            ('nota', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True,
                validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
            ('politica', models.JSONField(blank=True, default=dict)),
            ('documento', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                related_name='control_automatico', to='documentos.documentoexpediente')),
            ('recurso', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='controles_automaticos_documentales', to='recursos.recurso')),
        ],
        options={'verbose_name': 'Control automático del documento',
            'verbose_name_plural': 'Controles automáticos de documentos',
            'constraints': [models.CheckConstraint(condition=models.Q(nota__isnull=True) |
                (models.Q(nota__gte=0) & models.Q(nota__lte=100)), name='control_automatico_nota_porcentaje')]})]
