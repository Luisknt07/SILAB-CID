"""Los anexos propios de planta piloto, centro experimental y observatorio dejan de llamarse «Informe de…».

Un anexo recoge los datos del período; el análisis va en el informe semestral. Los seis anexos
propios pasan a nombrarse por lo que registran, con el mismo patrón que los cinco comunes
(«Tema: detalle»).

Solo cambia el nombre que coincide con el del catálogo distribuido: un nombre editado por la
institución se conserva. Se puede aplicar más de una vez y se puede revertir.
"""
from django.db import migrations

NOMBRES = {
    'PP-PRODUCCION': ('Informe de producción de la planta piloto: órdenes, lotes y entregas',
                      'Producción de la planta piloto: órdenes, lotes y entregas'),
    'PP-CALIDAD': ('Informe de control de calidad y no conformidades de la planta piloto',
                   'Control de calidad de la planta piloto: controles y no conformidades'),
    'CE-ENSAYOS': ('Informe de ensayos y seguimiento de parcelas experimentales',
                   'Ensayos del centro experimental: parcelas y seguimiento'),
    'OBS-DATOS': ('Registro de fuentes, metodología y actualización de indicadores del observatorio',
                  'Datos del observatorio: fuentes, metodología y actualización de indicadores'),
    'OBS-BOLETINES': ('Informe de publicaciones y cumplimiento del calendario del observatorio',
                      'Publicaciones del observatorio: boletines y calendario'),
    'OBS-EVENTOS': ('Informe de socialización de resultados y vinculación del observatorio',
                    'Socialización del observatorio: eventos y participantes'),
}


def _cambiar(apps, schema_editor, desde, hacia):
    modelo = apps.get_model('documentos', 'DocumentoExigido')
    for exigido in modelo.objects.using(schema_editor.connection.alias).filter(codigo__in=NOMBRES):
        nombres = NOMBRES[exigido.codigo]
        if exigido.nombre == nombres[desde]:
            exigido.nombre = nombres[hacia]
            exigido.save(update_fields=['nombre'])


def renombrar(apps, schema_editor):
    _cambiar(apps, schema_editor, 0, 1)


def restituir(apps, schema_editor):
    _cambiar(apps, schema_editor, 1, 0)


class Migration(migrations.Migration):
    dependencies = [('documentos', '0025_anexos_del_informe')]
    operations = [migrations.RunPython(renombrar, restituir)]
