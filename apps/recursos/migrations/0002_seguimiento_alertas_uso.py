from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('recursos', '0001_propiedad_modelos')]
    operations = [
        migrations.AlterField(model_name='alertausoequipo', name='motivo', field=models.CharField(max_length=20,
            choices=[('sin_uso', 'Sin uso acreditado en 6 meses'),
                     ('sin_registros', 'Sin uso acreditado; revisar registros'),
                     ('pendiente', 'Cierres de uso por completar'),
                     ('poco_uso', 'Poco uso acreditado (menos de 12 horas al año)')])),
        migrations.AddField(model_name='alertausoequipo', name='plan_uso', field=models.TextField(blank=True,
            verbose_name='Compromiso para aprovechar el equipo',
            help_text='Actividades previstas, responsable y evidencia que permitirá comprobar su ejecución.')),
        migrations.AddField(model_name='alertausoequipo', name='notificada_en', field=models.DateField(blank=True, null=True,
            verbose_name='Fecha de comunicación a la unidad',
            help_text='Registra una comunicación realizada. Completar este campo no envía mensajes.')),
        migrations.AddField(model_name='alertausoequipo', name='revisar_desde', field=models.DateField(blank=True, null=True,
            verbose_name='Revisar posible redistribución desde',
            help_text='La Dirección fija el plazo de corrección; no se aplica un plazo automático.')),
        migrations.AddField(model_name='alertausoequipo', name='evidencia', field=models.JSONField(blank=True, default=dict,
            editable=False, verbose_name='Última lectura acreditada')),
        migrations.AddField(model_name='alertausoequipo', name='ultima_revision', field=models.DateField(blank=True, null=True,
            editable=False, verbose_name='Última revisión de uso')),
    ]
