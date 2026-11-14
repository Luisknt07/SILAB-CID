from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('reservas', '0001_propiedad_modelos')]
    operations = [
        migrations.AddField(
            model_name='asistentevisita', name='rol',
            field=models.CharField(blank=True, default='', max_length=20,
                                   choices=[('estudiante', 'Estudiante'), ('docente', 'Profesor'),
                                            ('administrativo', 'Administrativo'), ('otro', 'Otro')]),
        ),
        migrations.AddField(
            model_name='asistentevisita', name='telefono',
            field=models.CharField('Celular', blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='asistentevisita', name='correo',
            field=models.EmailField(blank=True, default='', max_length=254),
        ),
    ]
