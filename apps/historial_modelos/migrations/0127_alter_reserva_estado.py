from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webcitt", "0126_responsableunidad_contacto_publico"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reserva",
            name="estado",
            field=models.CharField(
                choices=[
                    ("pendiente", "Pendiente"),
                    ("confirmada", "Confirmada"),
                    ("en_proceso", "En Proceso"),
                    ("completada", "Completada"),
                    ("rechazada", "Rechazada"),
                    ("cancelada", "Cancelada"),
                    ("no_presentado", "No se Presentó"),
                ],
                default="pendiente",
                help_text="Estado actual de la reserva",
                max_length=20,
            ),
        ),
    ]
