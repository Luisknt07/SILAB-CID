from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0188_equiposservicios_familia_tecnologica_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='unidad',
            name='video_unidad',
            field=models.URLField(
                blank=True,
                help_text=(
                    'Enlace de YouTube para la presentación pública de esta unidad. '
                    'Si se omite, se conserva el video institucional.'
                ),
                max_length=500,
                verbose_name='Video de presentación de la unidad',
            ),
        ),
    ]
