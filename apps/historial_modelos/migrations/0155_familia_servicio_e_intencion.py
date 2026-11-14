from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webcitt", "0154_iva_configurable"),
    ]

    operations = [
        migrations.AddField(
            model_name="fablabservice",
            name="familia",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Agrupa los servicios afines en el catálogo (por ejemplo, Impresión 3D). "
                    "Vacío usa el tipo de servicio."
                ),
                max_length=80,
                verbose_name="Familia o categoría del servicio",
            ),
        ),
        migrations.AddField(
            model_name="reserva",
            name="intencion_solicitud",
            field=models.TextField(
                blank=True,
                help_text=(
                    "Lo que la persona pretende realizar (50 a 200 palabras): orienta la revisión "
                    "y las sugerencias de la guía sin publicarse en ella."
                ),
            ),
        ),
    ]
