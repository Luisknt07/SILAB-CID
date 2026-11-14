from django.db import migrations, models

import apps.formacion.models.enlaces_formacion


class Migration(migrations.Migration):
    dependencies = [('webcitt', '0326_indices_aforo_cursos')]

    operations = [
        migrations.AddField(model_name='curso', name='activo', field=models.BooleanField(
            default=True, help_text='Desactiva la oferta sin borrar contenidos ni el historial de sus participantes.', verbose_name='Activo')),
        migrations.AddField(model_name='curso', name='origen', field=models.CharField(
            choices=[('nativo', 'En esta plataforma'), ('externo', 'Plataforma externa')], default='nativo', max_length=10, verbose_name='Dónde se realiza')),
        migrations.AddField(model_name='curso', name='url_externa', field=models.URLField(
            blank=True, max_length=1000, validators=[apps.formacion.models.enlaces_formacion.validar_enlace_formacion], verbose_name='Enlace de la actividad externa')),
        migrations.AddField(model_name='curso', name='entidad_organizadora', field=models.CharField(
            blank=True, max_length=200, verbose_name='Institución organizadora')),
        migrations.AddField(model_name='curso', name='participacion_unidad', field=models.CharField(
            choices=[('organizador', 'Organizador'), ('coorganizador', 'Coorganizador'), ('colaborador', 'Colaborador'), ('difusor', 'Difusión académica')],
            default='organizador', max_length=14, verbose_name='Participación de la unidad')),
        migrations.AlterField(model_name='curso', name='clasificacion', field=models.CharField(
            choices=[('corto', 'Curso corto'), ('largo', 'Curso largo'), ('taller', 'Taller'), ('capacitacion', 'Capacitación'),
                     ('induccion', 'Inducción'), ('entrenamiento', 'Entrenamiento técnico'), ('webinar', 'Webinar'),
                     ('seminario', 'Seminario'), ('conferencia', 'Conferencia'), ('congreso', 'Congreso'),
                     ('jornada', 'Jornada'), ('encuentro', 'Encuentro')], default='corto', max_length=16, verbose_name='Clasificación')),
        migrations.AddIndex(model_name='curso', index=models.Index(
            fields=['unidad', 'publicado', 'activo', 'orden', 'nombre'], name='curso_unidad_oferta_orden_idx')),
        migrations.AddIndex(model_name='curso', index=models.Index(
            fields=['unidad', 'orden', 'nombre'], name='curso_unidad_orden_nombre_idx')),
    ]
