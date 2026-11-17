from django.db import migrations, models


def comprobar_identidades(apps, schema_editor):
    Componente = apps.get_model("centros_id", "Componente")
    alias = schema_editor.connection.alias
    duplicados = (
        Componente.objects.using(alias)
        .exclude(unidad_slug="")
        .values("unidad_slug")
        .annotate(total=models.Count("pk"))
        .filter(total__gt=1)
    )
    if duplicados.exists():
        raise RuntimeError(
            "Hay instalaciones propias repetidas en Centros. Revise sus adscripciones "
            "antes de aplicar esta migración; no se han fusionado ni borrado registros."
        )


class Migration(migrations.Migration):
    dependencies = [("centros_id", "0017_organizacion_areas_operaciones")]
    operations = [
        migrations.RunPython(comprobar_identidades, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="componente",
            constraint=models.UniqueConstraint(
                fields=("unidad_slug",),
                condition=~models.Q(unidad_slug=""),
                name="cid_laboratorio_propio_unico",
            ),
        ),
    ]
