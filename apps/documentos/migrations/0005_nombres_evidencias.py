"""Aclara los nombres del catálogo estándar; conserva los personalizados."""
from django.db import migrations

NOMBRES = (
    ('GUIAS', 'Guías de práctica aprobadas y su vínculo con el syllabus',
     'Guías de prácticas: aprobación y vínculo con el syllabus'),
    ('INDUCCION-SEGURIDAD', 'Registro de inducción de seguridad a usuarios nuevos',
     'Seguridad y condiciones de operación: protocolo, inducciones y controles'),
    ('INVESTIGACION', 'Investigación aplicada y desarrollo tecnológico en la unidad',
     'Resultados de investigación aplicada y desarrollo tecnológico'),
    ('TRANSFERENCIA', 'Transferencia de conocimiento y servicios a la sociedad',
     'Transferencia de conocimiento y servicios especializados a la sociedad'),
)


def renombrar(apps, schema_editor, inverso=False):
    modelo = apps.get_model('documentos', 'DocumentoExigido')
    for codigo, anterior, nuevo in NOMBRES:
        origen, destino = (nuevo, anterior) if inverso else (anterior, nuevo)
        modelo.objects.using(schema_editor.connection.alias).filter(codigo=codigo, nombre=origen).update(nombre=destino)


def revertir(apps, schema_editor):
    renombrar(apps, schema_editor, inverso=True)


class Migration(migrations.Migration):
    dependencies = [('documentos', '0004_detalle_resultados_gestion')]
    operations = [migrations.RunPython(renombrar, revertir)]
