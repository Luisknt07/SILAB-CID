"""El uso del equipo se cobra cuando el laboratorio ejecuta el trabajo."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webcitt", "0156_cancelacion_trazable"),
    ]

    operations = [
        migrations.AddField(
            model_name="configuracionoperativaunidad",
            name="cobrar_uso_equipo_ejecucion",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Aplica cuando el laboratorio opera la máquina por la persona: "
                    "entrega del modelo listo o diseño completo. Las horas de máquina "
                    "se trasladan con el descuento del segmento (estudiante, personal "
                    "o externo). Con asesoría en la unidad el equipo va reservado y se "
                    "mantiene como referencia."
                ),
                verbose_name="Cobrar el uso de equipo cuando el laboratorio ejecuta",
            ),
        ),
    ]
