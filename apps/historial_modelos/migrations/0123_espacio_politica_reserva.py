from django.db import migrations, models


def clasificar_espacios_existentes(apps, schema_editor):
    EspacioReservable = apps.get_model('webcitt', 'EspacioReservable')
    tecnicos = EspacioReservable.objects.filter(
        equipos_asociados__isnull=False,
    ).values_list('pk', flat=True).distinct()
    EspacioReservable.objects.filter(pk__in=tecnicos).update(
        politica_reserva='tecnico',
    )
    EspacioReservable.objects.exclude(pk__in=tecnicos).update(
        politica_reserva='general',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0122_espacio_mobiliario_equipos_asociados'),
    ]

    operations = [
        migrations.AddField(
            model_name='espacioreservable',
            name='politica_reserva',
            field=models.CharField(
                choices=[
                    ('general', 'Uso general: puede reservarse solo con mobiliario'),
                    ('mixto', 'Uso mixto: espacio solo o con recursos técnicos'),
                    ('tecnico', 'Uso técnico: exige equipo o software asociado'),
                ],
                default='mixto',
                help_text=(
                    'Define si el espacio puede reservarse únicamente con su mobiliario, '
                    'si admite ambos usos o si siempre exige un equipo o software asociado.'
                ),
                max_length=20,
                verbose_name='Política de reserva',
            ),
        ),
        migrations.AlterField(
            model_name='espacioreservable',
            name='equipos_asociados',
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    'Equipos técnicos ubicados o disponibles en este espacio. La '
                    'política de reserva determina si su selección es obligatoria '
                    'u opcional.'
                ),
                related_name='espacios_asociados',
                to='webcitt.unidadequipo',
            ),
        ),
        migrations.RunPython(
            clasificar_espacios_existentes,
            migrations.RunPython.noop,
        ),
    ]
