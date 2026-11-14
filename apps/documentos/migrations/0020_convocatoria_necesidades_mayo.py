"""Ajusta únicamente la ventana estándar; los plazos archivados se conservan."""
from django.db import migrations


def ajustar_ventana(apps, schema_editor):
    modelo = apps.get_model('documentos', 'DocumentoExigido')
    modelo.objects.using(schema_editor.connection.alias).filter(
        codigo='PLAN-COMPRAS-ANUAL', periodicidad='anual', plazo_regla='meses',
        abre_mes=5, vence_mes=8, fecha_limite__isnull=True,
    ).update(vence_mes=5)


class Migration(migrations.Migration):
    dependencies = [('documentos', '0019_editor_protocolo_seguridad')]
    # No se deshace una preferencia de la institución ni se cambian entregas.
    operations = [migrations.RunPython(ajustar_ventana, migrations.RunPython.noop)]
