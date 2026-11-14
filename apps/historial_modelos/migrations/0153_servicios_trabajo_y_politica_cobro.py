from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webcitt", "0152_figuras_guia_borrador"),
    ]

    operations = [
        migrations.AddField(
            model_name="configuracionoperativaunidad",
            name="cobrar_tarifa_base",
            field=models.BooleanField(
                default=False,
                help_text="Desactivado: la tarifa base se muestra como referencia y la asume la Universidad.",
                verbose_name="Cobrar la tarifa base del servicio",
            ),
        ),
        migrations.AddField(
            model_name="configuracionoperativaunidad",
            name="cobrar_uso_equipo",
            field=models.BooleanField(
                default=False,
                help_text="Horas de máquina estimadas por pieza multiplicadas por el costo hora del servicio.",
                verbose_name="Cobrar el uso de equipo",
            ),
        ),
        migrations.AddField(
            model_name="configuracionoperativaunidad",
            name="cobrar_mano_obra",
            field=models.BooleanField(
                default=False,
                help_text="Horas de trabajo técnico estimadas por pieza multiplicadas por su costo hora.",
                verbose_name="Cobrar la mano de obra",
            ),
        ),
        migrations.AddField(
            model_name="configuracionoperativaunidad",
            name="cobrar_diseno",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Aplica cuando el laboratorio diseña (asistido o completo). "
                    "Los materiales se cobran siempre según el consumo."
                ),
                verbose_name="Cobrar el diseño realizado por el laboratorio",
            ),
        ),
        migrations.AddField(
            model_name="reserva",
            name="urgencia_servicio",
            field=models.CharField(
                blank=True,
                choices=[
                    ("normal", "Atención normal según la cola de trabajo"),
                    ("urgente", "Urgente: 1 a 2 días laborables"),
                ],
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="reserva",
            name="cantidad_piezas",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Número de piezas o ejemplares del trabajo solicitado.",
            ),
        ),
        migrations.AddField(
            model_name="reserva",
            name="detalle_trabajo",
            field=models.TextField(
                blank=True,
                help_text="Dimensiones, acabado u otras precisiones del trabajo.",
            ),
        ),
        migrations.AddField(
            model_name="reserva",
            name="fecha_entrega_prevista",
            field=models.DateField(
                blank=True,
                help_text="Entrega propuesta por el sistema según la cola de trabajo; la unidad puede ajustarla.",
                null=True,
            ),
        ),
    ]
