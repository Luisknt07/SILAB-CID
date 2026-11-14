from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0117_actividades_guias_programacion_reservas'),
    ]

    operations = [
        migrations.AddField(
            model_name='guiaactividadreserva',
            name='permite_descarga',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Permite que los usuarios autorizados descarguen el PDF. '
                    'Si se desactiva, la guía queda disponible únicamente para visualización.'
                ),
            ),
        ),
    ]
