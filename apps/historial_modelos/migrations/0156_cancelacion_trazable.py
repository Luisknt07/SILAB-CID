from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("webcitt", "0155_familia_servicio_e_intencion"),
    ]

    operations = [
        migrations.AddField(
            model_name="reserva",
            name="cancelada_en",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="reserva",
            name="cancelada_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reservas_canceladas",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="reserva",
            name="origen_cancelacion",
            field=models.CharField(
                blank=True,
                choices=[("solicitante", "Solicitante"), ("laboratorio", "Laboratorio")],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="reserva",
            name="motivo_cancelacion",
            field=models.TextField(blank=True),
        ),
    ]
