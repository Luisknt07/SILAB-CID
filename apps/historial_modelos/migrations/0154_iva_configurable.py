from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webcitt", "0153_servicios_trabajo_y_politica_cobro"),
    ]

    operations = [
        migrations.AddField(
            model_name="configuracionoperativaunidad",
            name="aplicar_iva",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Agrega el IVA sobre el valor a cargo del usuario en estimaciones, "
                    "comprobantes y liquidaciones. Desactivado mientras no se declare."
                ),
                verbose_name="Aplicar IVA al valor del usuario",
            ),
        ),
        migrations.AddField(
            model_name="configuracionoperativaunidad",
            name="porcentaje_iva",
            field=models.DecimalField(
                decimal_places=2,
                default=15,
                help_text="Porcentaje vigente del impuesto al valor agregado.",
                max_digits=5,
                validators=[MinValueValidator(0), MaxValueValidator(100)],
                verbose_name="Porcentaje de IVA",
            ),
        ),
    ]
