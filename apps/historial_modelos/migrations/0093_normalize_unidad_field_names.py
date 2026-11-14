from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0092_rename_proyecto_unidad'),
    ]

    operations = [
        migrations.RenameField(
            model_name='unidad',
            old_name='tipo_proyecto',
            new_name='area_conocimiento',
        ),
        migrations.RenameField(
            model_name='softwaredisponible',
            old_name='proyecto',
            new_name='unidad',
        ),
        migrations.RenameField(
            model_name='integrante',
            old_name='proyecto',
            new_name='unidad',
        ),
        migrations.RenameField(
            model_name='fabricationjob',
            old_name='proyecto',
            new_name='unidad',
        ),
        migrations.RenameField(
            model_name='modulounidad',
            old_name='proyecto',
            new_name='unidad',
        ),
        migrations.RenameField(
            model_name='carpetarecurso',
            old_name='proyecto',
            new_name='unidad',
        ),
        migrations.RenameField(
            model_name='recurso',
            old_name='proyecto',
            new_name='unidad',
        ),
        migrations.RenameField(
            model_name='reglamentounidad',
            old_name='proyecto',
            new_name='unidad',
        ),
        migrations.AlterField(
            model_name='unidad',
            name='categorias',
            field=models.ManyToManyField(
                blank=True,
                help_text='Puede seleccionar hasta 6 categorías.',
                related_name='unidades',
                to='webcitt.categoria',
            ),
        ),
        migrations.AlterField(
            model_name='unidad',
            name='tipos_laboratorio',
            field=models.ManyToManyField(
                blank=True,
                help_text='Seleccione los tipos de laboratorio (puede ser múltiple).',
                related_name='unidades',
                to='webcitt.tipolaboratorio',
            ),
        ),
    ]
