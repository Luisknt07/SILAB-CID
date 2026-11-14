from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('gestion_unidades', '0001_propiedad_modelos')]
    operations = [
        migrations.AddField(
            model_name='elementofichaarea', name='solo_referencia',
            field=models.BooleanField(
                default=False, verbose_name='Dotación propuesta',
                help_text='Referencia para evaluar una capacidad futura. No crea equipos físicos, existencias ni licencias al sincronizar.'),
        ),
    ]
