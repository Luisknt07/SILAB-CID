from django.db import migrations, models


PERMISOS_LEGADOS = {
    "reservas": True,
    "agenda": True,
    "recursos": True,
    "mantenimiento": True,
    "inventario": True,
    "practicas": True,
    "reportes": True,
    "configuracion": True,
    "corregir_cerradas": False,
}


def conservar_accesos_existentes(apps, schema_editor):
    ResponsableUnidad = apps.get_model("webcitt", "ResponsableUnidad")
    for responsable in ResponsableUnidad.objects.all().iterator():
        if responsable.recibe_reservas or responsable.rol == "coordinacion":
            permisos = dict(PERMISOS_LEGADOS)
            permisos["corregir_cerradas"] = responsable.rol == "coordinacion"
            ResponsableUnidad.objects.filter(pk=responsable.pk).update(
                permisos_operativos=permisos
            )


class Migration(migrations.Migration):
    dependencies = [
        ("webcitt", "0133_notificacion_reserva_reintentos_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="responsableunidad",
            name="permisos_operativos",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Permisos granulares del panel de gestión. Un valor ausente conserva "
                    "la configuración recomendada para el rol."
                ),
            ),
        ),
        migrations.RunPython(
            conservar_accesos_existentes,
            migrations.RunPython.noop,
        ),
    ]
