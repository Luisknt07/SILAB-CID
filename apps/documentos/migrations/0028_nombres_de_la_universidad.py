"""Anexos del informe: nombres con la redacción de la universidad.

documentos.0027 había recortado varios nombres. Quien revisa busca cada exigencia por su texto, así que
los anexos lo llevan completo. Solo se apartan de él donde hay un motivo:

- «Registros de uso»: la planificación de la misma exigencia es el documento principal.
- «Reportes de seguridad y condiciones de operación»: el protocolo de bioseguridad es el documento principal.
- «Fichas técnicas…»: el inventario de la misma evidencia es otro anexo.
- El nombre se adapta al tipo de unidad (planta piloto, centro experimental u observatorio).

Solo se reemplaza un nombre idéntico al del catálogo distribuido; lo editado por la institución se
conserva. Se puede aplicar más de una vez y se puede revertir.
"""
from django.db import migrations

# código: (nombre de documentos.0027, nombre con la redacción de la universidad)
NOMBRES = {
    'EQUIPAMIENTO': ('Plan de mantenimiento de equipos e informe de equipamiento, disponibilidad y funcionalidad',
                     'Plan de mantenimiento de equipos e informes de equipamiento, disponibilidad y funcionalidad'),
    'FICHAS-TECNICAS': ('Fichas técnicas de laboratorios, talleres, software, simuladores y espacios',
                        'Fichas técnicas de laboratorios, talleres, software, simuladores y espacios utilizados'),
    'PRACTICAS-FT02': ('Planificación semestral de las prácticas',
                       'Planificación semestral de las prácticas por asignatura, unidad, fecha, escenario y '
                       'responsable'),
    'GUIAS': ('Guías de prácticas', 'Guías de prácticas aprobadas y vinculadas con los contenidos del syllabus'),
    'PRACTICAS-FT03': ('Registros de asistencia y evidencias de las prácticas',
                       'Registros de asistencia, bitácoras, fotografías identificadas, capturas de simuladores, '
                       'informes de estudiantes y productos desarrollados'),
    'DESECHOS': ('Registros de gestión de desechos peligrosos y especiales',
                 'Registros de gestión de desechos peligrosos y especiales, conforme a la normativa aplicable'),
    'INVESTIGACION': ('Informe de resultados de investigación aplicada y desarrollo tecnológico',
                      'Informes de resultados de investigación aplicada y desarrollo tecnológico generados en '
                      'laboratorios y centros'),
    'TRANSFERENCIA': ('Informe de transferencia de conocimiento, tecnología y servicios especializados a la sociedad',
                      'Informes de transferencia de conocimiento, tecnología y prestación de servicios '
                      'especializados a la sociedad'),
}


def _renombrar(apps, schema_editor, origen, destino):
    modelo = apps.get_model('documentos', 'DocumentoExigido')
    alias = schema_editor.connection.alias
    for exigido in modelo.objects.using(alias).filter(codigo__in=NOMBRES.keys()):
        if exigido.nombre == NOMBRES[exigido.codigo][origen]:
            exigido.nombre = NOMBRES[exigido.codigo][destino]
            exigido.save(update_fields=['nombre'])


def con_la_redaccion_de_la_universidad(apps, schema_editor):
    _renombrar(apps, schema_editor, 0, 1)


def con_los_nombres_recortados(apps, schema_editor):
    _renombrar(apps, schema_editor, 1, 0)


class Migration(migrations.Migration):
    dependencies = [('documentos', '0027_anexos_por_exigencia')]
    operations = [migrations.RunPython(con_la_redaccion_de_la_universidad, con_los_nombres_recortados)]
