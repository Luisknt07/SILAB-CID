from django.db import migrations, models


def clasificar_vinculacion_existente(apps, schema_editor):
    Reserva = apps.get_model('webcitt', 'Reserva')
    Reserva.objects.filter(actividad_catalogo__isnull=False).update(
        vinculacion_actividad='catalogo'
    )
    Reserva.objects.filter(
        actividad_catalogo__isnull=True,
    ).exclude(referencia_actividad='').update(vinculacion_actividad='manual')


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0115_horarios_operativos_interperiodo'),
    ]

    operations = [
        migrations.AddField(
            model_name='reserva',
            name='vinculacion_actividad',
            field=models.CharField(
                choices=[
                    ('catalogo', 'Actividad registrada en el catálogo institucional'),
                    ('manual', 'Actividad formal informada por el solicitante'),
                    ('independiente', 'Uso autónomo sin actividad formal vinculada'),
                    ('no_aplica', 'No aplica'),
                ],
                db_index=True,
                default='no_aplica',
                help_text=(
                    'Distingue una referencia seleccionada del catálogo, una '
                    'referencia manual y un uso autónomo sin actividad formal.'
                ),
                max_length=20,
            ),
        ),
        migrations.RunPython(
            clasificar_vinculacion_existente,
            migrations.RunPython.noop,
        ),
    ]
