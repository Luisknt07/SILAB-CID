from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('gestion_unidades', '0002_dotacion_propuesta')]
    operations = [
        migrations.AlterField(
            model_name='configuracionoperativaunidad',
            name='acepta_visitas',
            field=models.BooleanField(
                'Acepta visitas', default=True,
                help_text='Permite solicitar visitas. Solo las áreas marcadas como visitables forman parte del recorrido publicado.',
            ),
        ),
    ]
