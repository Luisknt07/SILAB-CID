from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0119_alter_programacionreserva_frecuencia'),
    ]

    operations = [
        migrations.AddField(
            model_name='unidad',
            name='plano_espacios',
            field=models.ImageField(
                blank=True,
                help_text=(
                    'Imagen general con la distribución de áreas, estaciones, '
                    'accesos y zonas de circulación de la unidad.'
                ),
                null=True,
                upload_to='unidades/planos_espacios/',
                verbose_name='Plano o layout de los espacios',
            ),
        ),
        migrations.AddField(
            model_name='unidad',
            name='recorrido_360_ruta',
            field=models.CharField(
                blank=True,
                help_text=(
                    'URL https:// o ruta relativa dentro de archivos estáticos, '
                    'por ejemplo img/360/laboratorio/index.html.'
                ),
                max_length=500,
                verbose_name='Tour 360°',
            ),
        ),
        migrations.AddField(
            model_name='unidad',
            name='recorrido_espacios_youtube_url',
            field=models.URLField(
                blank=True,
                help_text=(
                    'Enlace de YouTube del recorrido público por las áreas de la unidad.'
                ),
                max_length=500,
                verbose_name='Video de recorrido por los espacios',
            ),
        ),
        migrations.AddField(
            model_name='reserva',
            name='alcance_espacio',
            field=models.CharField(
                choices=[
                    ('sin_espacio', 'No requiere espacio físico'),
                    ('areas', 'Una o varias áreas configuradas'),
                    ('espacio_unico', 'Espacio único de la unidad'),
                    ('unidad_completa', 'Unidad completa'),
                ],
                db_index=True,
                default='sin_espacio',
                help_text=(
                    'Conserva si la solicitud ocupa áreas concretas, el único '
                    'espacio disponible o toda la unidad.'
                ),
                max_length=20,
            ),
        ),
        migrations.RunSQL(
            sql=(
                "UPDATE webcitt_reserva SET alcance_espacio = CASE "
                "WHEN incluye_espacio = TRUE AND EXISTS ("
                "SELECT 1 FROM webcitt_reserva_espacios_solicitados rel "
                "WHERE rel.reserva_id = webcitt_reserva.id"
                ") THEN 'areas' "
                "WHEN incluye_espacio = TRUE THEN 'unidad_completa' "
                "ELSE 'sin_espacio' END"
            ),
            reverse_sql=(
                "UPDATE webcitt_reserva SET alcance_espacio = 'sin_espacio'"
            ),
        ),
    ]
