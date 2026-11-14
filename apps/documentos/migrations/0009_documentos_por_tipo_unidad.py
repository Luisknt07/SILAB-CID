"""Añade evidencias propias; no modifica personalizaciones ni documentos existentes."""
from django.db import migrations


NUEVOS = (
    ('PP-PRODUCCION', 'Informe de producción de la planta piloto: órdenes, lotes y entregas',
     'ejecucion', 'produccion', 'plantas_piloto', 90,
     'Producción realizada frente al plan, cantidades, estados y trazabilidad de lotes y entregas.'),
    ('PP-CALIDAD', 'Informe de control de calidad y no conformidades de la planta piloto',
     'evaluacion', 'control-calidad', 'plantas_piloto', 95,
     'Parámetros, mediciones y resultados por lote u orden; liberación, rechazo y seguimiento.'),
    ('CE-ENSAYOS', 'Informe de ensayos y seguimiento de parcelas experimentales',
     'evaluacion', 'ensayos', 'centro_experimental', 90,
     'Objetivo, escenario, fechas, manejo, mediciones y resultados respaldados de los ensayos.'),
    ('OBS-DATOS', 'Registro de fuentes, metodología y actualización de indicadores del observatorio',
     'ejecucion', 'datos-observatorio', 'observatorios', 20,
     'Fichas metodológicas, fuentes y actualizaciones con período de referencia, territorio y trazabilidad.'),
    ('OBS-BOLETINES', 'Informe de publicaciones y cumplimiento del calendario del observatorio',
     'evaluacion', 'boletines', 'observatorios', 30,
     'Publicaciones previstas y efectivas, fecha, responsable, indicadores y respaldo consultable.'),
    ('OBS-EVENTOS', 'Informe de socialización de resultados y vinculación del observatorio',
     'evaluacion', 'eventos', 'observatorios', 40,
     'Actividades realizadas, propósito, destinatarios, productos difundidos y respaldo.'),
)


def agregar(apps, schema_editor):
    exigido = apps.get_model('documentos', 'DocumentoExigido')
    alias = schema_editor.connection.alias
    padre = exigido.objects.using(alias).filter(codigo='INFORME-SEMESTRAL').first()
    # Una instalación nueva sin catálogo lo siembra completo cuando prepara
    # su primer expediente; no dejar anexos huérfanos como entregas separadas.
    if padre is None:
        return
    for codigo, nombre, carpeta, fuente, tipo, orden, descripcion in NUEVOS:
        exigido.objects.using(alias).get_or_create(codigo=codigo, defaults={
            'nombre': nombre, 'carpeta': carpeta, 'fuente_reporte': fuente,
            'periodicidad': 'semestral', 'origen': 'sistema', 'requiere_firma': False,
            'condicional': False, 'plazo_regla': 'fin', 'plazo_dias': 0,
            'tipos_unidad': [tipo], 'orden': orden, 'descripcion': descripcion,
            'activo': True, 'anexo_de_id': padre.pk})


class Migration(migrations.Migration):
    dependencies = [('documentos', '0008_control_automatico_documento')]
    operations = [migrations.RunPython(agregar, migrations.RunPython.noop)]
