from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webcitt", "0118_guiaactividadreserva_permite_descarga"),
    ]

    operations = [
        migrations.AlterField(
            model_name="programacionreserva",
            name="frecuencia",
            field=models.CharField(
                choices=[
                    ("unica", "Una sola sesión"),
                    ("semanal_rango", "Semanal hasta una fecha definida"),
                    ("semanal_periodo", "Semanal durante el período académico"),
                ],
                default="unica",
                max_length=20,
            ),
        ),
    ]
