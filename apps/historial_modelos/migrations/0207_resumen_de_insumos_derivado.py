"""El resumen de insumos de cada activo sale de la relacion estructurada.

Los activos con insumos compatibles registrados reciben el texto derivado;
los que solo tienen el texto de cargas anteriores lo conservan tal cual.
"""

from django.db import migrations


def derivar_resumen(apps, schema_editor):
    UnidadEquipo = apps.get_model('webcitt', 'UnidadEquipo')
    Consumible = apps.get_model('webcitt', 'Consumible')
    for activo in UnidadEquipo.objects.all().iterator():
        nombres = list(Consumible.objects.filter(
            por_equipo__equipo_id=activo.equipo_id, unidad_id=activo.laboratorio_id,
        ).order_by('nombre').values_list('nombre', flat=True))
        if nombres:
            UnidadEquipo.objects.filter(pk=activo.pk).update(
                requiere_insumos=True, insumos_necesarios=", ".join(nombres))


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0206_clasificaciones_administrables'),
    ]

    operations = [
        migrations.RunPython(derivar_resumen, migrations.RunPython.noop),
    ]
