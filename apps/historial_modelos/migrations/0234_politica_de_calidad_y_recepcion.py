"""La Dirección recibe y califica; el decanato recibe el informe y no aprueba.

La cadena anterior pedía que cada decanato aprobara antes de que la Dirección
pudiera evaluar: una firma más para algo que el responsable de la unidad ya
declaró verídico. Ahora la unidad valida lo suyo, la Dirección decide si cumple
—y puede dar por recibida una entrega que la unidad archivó sin validar— y lo
evaluado se remite al decanato como informe para que resuelva lo que le toca.

Con eso, el mínimo de cumplimiento deja de estar escrito en el código: vive en
la política de calidad, junto con lo que cuesta entregar fuera de plazo.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def politica_y_grupo(apps, _schema_editor):
    """Siembra la política con los valores vigentes y renombra el grupo de la cadena anterior."""
    PoliticaDeCalidad = apps.get_model('webcitt', 'PoliticaDeCalidad')
    PoliticaDeCalidad.objects.get_or_create(pk=1)
    Group = apps.get_model('auth', 'Group')
    grupo = Group.objects.filter(name='Aprobación de expedientes').first()
    if grupo and not Group.objects.filter(name='Recepción de informes de calidad').exists():
        grupo.name = 'Recepción de informes de calidad'
        grupo.save(update_fields=['name'])


def deshacer_grupo(apps, _schema_editor):
    Group = apps.get_model('auth', 'Group')
    grupo = Group.objects.filter(name='Recepción de informes de calidad').first()
    if grupo and not Group.objects.filter(name='Aprobación de expedientes').exists():
        grupo.name = 'Aprobación de expedientes'
        grupo.save(update_fields=['name'])


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('webcitt', '0233_cadena_de_aprobacion'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PoliticaDeCalidad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minimo_cumplimiento', models.PositiveSmallIntegerField(
                    default=70, verbose_name='Mínimo de cumplimiento (%)',
                    help_text='Por debajo de este porcentaje la unidad no cumple y pasa a mejora continua.')),
                ('penalizacion_entrega_tardia', models.PositiveSmallIntegerField(
                    default=20, verbose_name='Penalización por entregar fuera de plazo (puntos)',
                    help_text='Se descuenta de la calificación de la entrega que la Dirección recibió '
                              'vencido el plazo.')),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('actualizado_por', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Política de calidad del expediente',
                'verbose_name_plural': 'Política de calidad del expediente',
            },
        ),
        migrations.RenameField(model_name='documentoexpediente', old_name='aprobado_en', new_name='recibido_en'),
        migrations.RenameField(model_name='documentoexpediente', old_name='aprobado_por', new_name='recibido_por'),
        migrations.AlterField(
            model_name='documentoexpediente',
            name='recibido_por',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='documentos_expediente_recibidos', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='documentoexpediente',
            name='entregado_tarde',
            field=models.BooleanField(default=False, verbose_name='Entregado fuera de plazo'),
        ),
        migrations.AddField(
            model_name='documentoexpediente',
            name='tardanza_motivo',
            field=models.TextField(
                blank=True, verbose_name='Motivo para entregar fuera de plazo',
                help_text='Lo que expone el responsable de la unidad para entregar vencido el plazo.'),
        ),
        migrations.AddField(
            model_name='documentoexpediente',
            name='tardanza_pedida_en',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='documentoexpediente',
            name='tardanza_habilitada_en',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='documentoexpediente',
            name='tardanza_habilitada_por',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='documentos_expediente_habilitados', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RenameField(
            model_name='dependenciaacademica', old_name='aprobadores', new_name='receptores'),
        migrations.AlterField(
            model_name='dependenciaacademica',
            name='receptores',
            field=models.ManyToManyField(
                blank=True, related_name='dependencias_que_recibe', to=settings.AUTH_USER_MODEL,
                verbose_name='Quiénes reciben el informe',
                help_text='Reciben el informe de cumplimiento de sus unidades y designan a sus responsables.'),
        ),
        migrations.RunPython(politica_y_grupo, deshacer_grupo),
    ]
