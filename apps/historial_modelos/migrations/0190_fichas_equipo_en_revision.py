from django.db import migrations


def corregir_estado_fichas_equipo(apps, schema_editor):
    FichaContenido = apps.get_model('webcitt', 'FichaContenido')
    FichaContenido.objects.filter(
        unidad__dependencia='plantas_piloto',
        tipo='equipo',
        estado='publicada',
    ).update(estado='en_revision')


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0189_unidad_video_unidad'),
    ]

    operations = [
        migrations.RunPython(
            corregir_estado_fichas_equipo,
            migrations.RunPython.noop,
        ),
    ]
