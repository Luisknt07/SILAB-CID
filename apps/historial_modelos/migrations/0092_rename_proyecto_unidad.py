from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('webcitt', '0091_remove_presentacionunidad_proyecto_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Proyecto',
            new_name='Unidad',
        ),
        migrations.AlterModelOptions(
            name='unidad',
            options={
                'verbose_name': 'Unidad',
                'verbose_name_plural': 'Unidades',
            },
        ),
        migrations.AlterField(
            model_name='carpetarecurso',
            name='proyecto',
            field=models.ForeignKey(
                help_text='Unidad a la que pertenece esta carpeta.',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='carpetas',
                to='webcitt.unidad',
            ),
        ),
        migrations.AlterField(
            model_name='recurso',
            name='proyecto',
            field=models.ForeignKey(
                help_text='Unidad a la que pertenece este recurso.',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='recursos',
                to='webcitt.unidad',
            ),
        ),
        migrations.AlterField(
            model_name='unidad',
            name='administrador',
            field=models.ForeignKey(
                blank=True,
                help_text='Usuario administrador asignado a la unidad',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='unidades_administradas',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='unidad',
            name='dependencia',
            field=models.CharField(
                blank=True,
                choices=[
                    ('centro_experimental', 'Centro Experimental'),
                    ('laboratorios', 'Laboratorio'),
                    ('observatorios', 'Observatorio'),
                    ('plantas_piloto', 'Planta Piloto'),
                ],
                help_text='Seleccione el tipo de unidad.',
                max_length=50,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='unidad',
            name='tipo_proyecto',
            field=models.CharField(
                blank=True,
                choices=[
                    ('ingenieria', 'Ingeniería y Sistemas Productivos'),
                    ('ia', 'Inteligencia Artificial, Ciencia de Datos y Ciberseguridad'),
                    ('biotecnologia', 'Biotecnología y Ciencias Biológicas Aplicadas'),
                    ('salud', 'Ciencias de la Salud y Formación Clínica'),
                    ('agro', 'Agroindustria, Tecnologías de Alimentos y Sostenibilidad Productiva'),
                    ('comunicacion', 'Tecnologías Inmersivas, Comunicación y Medios Digitales'),
                    ('Educacion', 'Educación, Innovación y Desarrollo Territorial'),
                    ('formacion', 'Formación Integral y Desarrollo Humano'),
                    ('otro', 'Otro'),
                ],
                help_text='Seleccione el área de conocimiento de la unidad.',
                max_length=50,
                null=True,
            ),
        ),
    ]
