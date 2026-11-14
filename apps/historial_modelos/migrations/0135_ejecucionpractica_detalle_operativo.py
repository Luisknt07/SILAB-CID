from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webcitt", "0134_responsableunidad_permisos_operativos"),
    ]

    operations = [
        migrations.AddField(
            model_name="ejecucionpractica",
            name="detalle_operativo",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Fotografía estructurada de participantes, equipos, software, "
                    "espacios, servicios e insumos utilizados durante la práctica."
                ),
            ),
        ),
    ]
