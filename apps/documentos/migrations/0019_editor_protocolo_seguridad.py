"""Habilita el editor estándar sin reemplazar documentos ni personalizaciones."""
from django.db import migrations

ANTERIOR = 'Protocolo de bioseguridad y condiciones de operación'
NUEVO = 'Protocolo de seguridad y condiciones de operación'


def habilitar(apps, schema_editor):
    modelo = apps.get_model('documentos', 'DocumentoExigido')
    modelo.objects.using(schema_editor.connection.alias).filter(
        codigo='PROTOCOLO-BIOSEGURIDAD', nombre__in=(ANTERIOR, NUEVO),
        fuente_reporte='', origen='unidad', periodicidad='unica', anexo_de__isnull=True,
    ).update(nombre=NUEVO, origen='ambos', fuente_reporte='protocolo', descripcion=(
        'Protocolo permanente elaborado con el editor: alcance, responsables, peligros, controles, '
        'operación y emergencias. Incluye medidas específicas según las actividades de la unidad. '
        'Se envía y aprueba en la plataforma con QR; se actualiza cuando cambian sus condiciones.'))


class Migration(migrations.Migration):
    dependencies = [('documentos', '0018_presentacion_documento_por_estado')]
    # Volver atrás no retira la fuente de documentos que ya se hayan redactado.
    operations = [migrations.RunPython(habilitar, migrations.RunPython.noop)]
