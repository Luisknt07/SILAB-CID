"""La ubicación de una unidad vive en un solo campo.

`laboratorio` era un texto libre con la ubicación, anterior a `ubicacion`.
Trece unidades tenían el dato en el campo viejo y el nuevo vacío. Se copia
donde falta y el campo viejo desaparece.
"""

from django.db import migrations


def copiar_ubicacion(apps, schema_editor):
    Unidad = apps.get_model('webcitt', 'Unidad')
    for unidad in Unidad.objects.exclude(laboratorio__isnull=True).exclude(laboratorio=''):
        if not (unidad.ubicacion or '').strip():
            unidad.ubicacion = unidad.laboratorio.strip()
            unidad.save(update_fields=['ubicacion'])


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0166_tres_tipos_de_usuario'),
    ]

    operations = [
        migrations.RunPython(copiar_ubicacion, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='unidad',
            name='laboratorio',
        ),
    ]
