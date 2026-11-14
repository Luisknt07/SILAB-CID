from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0109_catalogo_publico_y_tutoriales'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservaadjunto',
            name='indicaciones_visualizacion',
            field=models.TextField(
                blank=True,
                help_text=(
                    'Versión del software, programa recomendado, unidades, escala, '
                    'perfiles o cualquier consideración necesaria para revisar el archivo.'
                ),
                verbose_name='Indicaciones para abrir o visualizar',
            ),
        ),
    ]
