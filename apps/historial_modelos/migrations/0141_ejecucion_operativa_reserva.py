from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("webcitt", "0140_inventario_lotes_trazables"),
    ]

    operations = [
        migrations.AddField(
            model_name="reserva",
            name="detalle_ejecucion",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Registro estructurado de lo realmente ejecutado: asistencia, "
                    "recursos, consumos, incidencias y costos."
                ),
            ),
        ),
        migrations.AddField(
            model_name="reservaconsumible",
            name="cantidad_desperdiciada",
            field=models.DecimalField(
                decimal_places=3,
                default=0,
                help_text="Cantidad adicional retirada por falla, calidad o proceso.",
                max_digits=12,
            ),
        ),
        migrations.AddField(
            model_name="entradainventario",
            name="clave_idempotencia",
            field=models.CharField(
                blank=True,
                editable=False,
                help_text="Evita descontar dos veces el mismo consumo durante un cierre.",
                max_length=160,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="movimientofinancierounidad",
            name="clave_idempotencia",
            field=models.CharField(
                blank=True,
                editable=False,
                help_text="Evita duplicar el ingreso generado por un mismo cierre operativo.",
                max_length=160,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="incidenciaequipo",
            name="reserva",
            field=models.ForeignKey(
                blank=True,
                help_text="Atencion durante la cual se detecto la incidencia, si aplica.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="incidencias_operativas",
                to="webcitt.reserva",
            ),
        ),
        migrations.AddConstraint(
            model_name="reservaconsumible",
            constraint=models.CheckConstraint(
                check=models.Q(cantidad_desperdiciada__gte=0),
                name="reserva_consumible_desperdicio_no_negativo",
            ),
        ),
    ]
