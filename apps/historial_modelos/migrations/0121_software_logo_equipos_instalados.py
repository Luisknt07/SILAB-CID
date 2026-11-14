from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0120_unidad_multimedia_espacios_reserva_alcance'),
    ]

    operations = [
        migrations.AddField(
            model_name='softwaredisponible',
            name='logo',
            field=models.ImageField(
                blank=True,
                help_text=(
                    'Logo o icono visible en el catálogo de reservas. Se recomienda '
                    'una imagen cuadrada con fondo transparente.'
                ),
                null=True,
                upload_to='software/logos/',
            ),
        ),
        migrations.AddField(
            model_name='softwaredisponible',
            name='equipos_instalados',
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    'Equipos físicos de esta unidad donde está instalado o habilitado '
                    'el software. Para acceso por instalación debe seleccionarse al '
                    'menos uno.'
                ),
                limit_choices_to={'activa': True},
                related_name='software_instalado',
                to='webcitt.unidadequipo',
            ),
        ),
    ]
