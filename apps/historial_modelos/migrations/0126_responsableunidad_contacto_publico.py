from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0125_capacidadoperativaunidad_bloqueoagendaunidad_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='responsableunidad',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Breve descripción de su función o especialidad visible al solicitante.', max_length=240),
        ),
        migrations.AddField(
            model_name='responsableunidad',
            name='foto',
            field=models.ImageField(blank=True, help_text='Fotografía pública del responsable. Si se omite, se usa el avatar de su perfil institucional.', null=True, upload_to='unidades/responsables/'),
        ),
        migrations.AddField(
            model_name='responsableunidad',
            name='foto_referencial',
            field=models.CharField(blank=True, help_text='Ruta de una imagen estática usada únicamente para datos demostrativos.', max_length=255),
        ),
        migrations.AddField(
            model_name='responsableunidad',
            name='horario_atencion',
            field=models.CharField(blank=True, help_text='Horario o modalidad habitual de contacto.', max_length=120),
        ),
    ]
