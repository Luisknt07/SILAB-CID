"""El código de estudiante pasa a ser la cédula o documento de identidad.

Se renombra el campo en vez de crear otro: lo que ya estaba registrado
identifica a la misma persona y se conserva.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0158_carrera_turismo'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userprofile',
            old_name='codigo_estudiante',
            new_name='cedula',
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='cedula',
            field=models.CharField(
                blank=True,
                help_text=(
                    'Documento con el que la Universidad identifica a la persona. '
                    'Obligatorio para estudiantes; admite pasaporte o documento extranjero.'
                ),
                max_length=20,
                null=True,
                verbose_name='Cédula o documento de identidad',
            ),
        ),
    ]
