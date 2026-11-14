import json

from django.db import migrations, models


def inferir_intencion_historica(apps, schema_editor):
    Reserva = apps.get_model('webcitt', 'Reserva')
    reservas_con_software = set(
        Reserva.software_solicitado.through.objects.values_list(
            'reserva_id', flat=True,
        )
    )
    for reserva in Reserva.objects.all().iterator():
        tiene_software = reserva.pk in reservas_con_software
        try:
            recursos = json.loads(reserva.unidades_seleccionadas or '[]')
        except (TypeError, ValueError):
            recursos = []
        tiene_equipo = bool(recursos)
        # En datos anteriores no puede conocerse si el espacio físico fue elegido
        # o derivado. Solo se clasifica como intención explícita cuando no existen
        # recursos técnicos que lo expliquen.
        reserva.solicito_espacio = bool(
            reserva.incluye_espacio and not tiene_equipo and not tiene_software
        )
        reserva.solicito_equipo = bool(tiene_equipo and not tiene_software)
        reserva.solicito_software = tiene_software
        reserva.save(update_fields=[
            'solicito_espacio', 'solicito_equipo', 'solicito_software',
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0123_espacio_politica_reserva'),
    ]

    operations = [
        migrations.AddField(
            model_name='reserva',
            name='solicito_equipo',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text=(
                    'El usuario marcó explícitamente equipo o instrumento; se '
                    'distingue del puesto incorporado automáticamente por una licencia.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='reserva',
            name='solicito_espacio',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text=(
                    'El usuario marcó explícitamente espacio y mobiliario al iniciar; '
                    'se distingue del espacio incorporado por la ubicación de un equipo.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='reserva',
            name='solicito_software',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text=(
                    'El usuario marcó explícitamente software o licencia al iniciar.'
                ),
            ),
        ),
        migrations.RunPython(
            inferir_intencion_historica,
            migrations.RunPython.noop,
        ),
    ]
