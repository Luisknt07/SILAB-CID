from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0121_software_logo_equipos_instalados'),
    ]

    operations = [
        migrations.AddField(
            model_name='espacioreservable',
            name='mobiliario_incluido',
            field=models.TextField(
                blank=True,
                help_text=(
                    'Mesas, sillas, tomas eléctricas, red, proyector u otros '
                    'elementos que se incluyen automáticamente al reservar el '
                    'espacio y no se seleccionan como equipos técnicos.'
                ),
                verbose_name='Mobiliario e infraestructura incluidos',
            ),
        ),
        migrations.AddField(
            model_name='espacioreservable',
            name='equipos_asociados',
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    'Equipos técnicos ubicados o disponibles en este espacio. Si '
                    'existe al menos uno, el usuario deberá seleccionar un equipo '
                    'o software asociado.'
                ),
                related_name='espacios_asociados',
                to='webcitt.unidadequipo',
            ),
        ),
    ]
