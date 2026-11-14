from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("webcitt", "0132_reserva_cierre_notificaciones"),
    ]

    operations = [
        migrations.AddField(
            model_name="notificacionreserva",
            name="intentos_email",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="notificacionreserva",
            name="ultimo_intento_email",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
