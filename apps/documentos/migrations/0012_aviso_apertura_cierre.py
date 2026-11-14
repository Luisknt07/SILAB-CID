from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('documentos', '0011_referencias_indicadores')]

    operations = [
        migrations.AlterField(
            model_name='avisodocumental', name='tipo',
            field=models.CharField(choices=[
                ('recordatorio', 'Recordatorio de entrega'), ('apertura', 'Preparación del cierre'),
                ('ultimatum', 'Ultimátum de entrega'), ('evaluacion', 'Evaluación por no entrega')],
                default='recordatorio', max_length=20)),
    ]
