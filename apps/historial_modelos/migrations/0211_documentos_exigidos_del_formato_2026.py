"""Catalogo inicial de documentos exigidos, tomado del formato Planificacion 2026.

Cada fila dice en que carpeta va, quien la produce, cada cuanto y con que
plazo. Es un catalogo administrable: la institucion lo ajusta desde el admin.
"""

from django.db import migrations

DOCUMENTOS = (
    # codigo, nombre, carpeta, periodicidad, origen, firma, plazo_regla, plazo_dias, fuente, orden, descripcion
    ('RESOLUCION-CREACION', 'Resolución de creación de la unidad', 'planeacion', 'unica', 'unidad', False,
     'ninguno', 0, '', 10, 'Resolución que aprueba la unidad; se hereda cada año.'),
    ('PLANIFICACION-ANUAL', 'Planificación anual de la unidad (firmada)', 'planeacion', 'anual', 'unidad', True,
     'inicio', 15, '', 20, 'El plan del año con sus actividades, inventario, inversión y cronograma; se entrega '
                          'firmado en los primeros quince días del período.'),
    ('ORGANIGRAMA', 'Organigrama de la unidad', 'planeacion', 'unica', 'unidad', False, 'ninguno', 0, '', 30, ''),
    ('MANUAL-FUNCIONES', 'Manual de funciones', 'planeacion', 'unica', 'unidad', False, 'ninguno', 0, '', 40, ''),
    ('PLAN-MANTENIMIENTO', 'Plan anual de mantenimiento preventivo y correctivo', 'planeacion', 'anual',
     'sistema', False, 'fin', 0, 'mantenimiento', 50,
     'Definido en el informe del primer semestre; ejecución mínima del 80 % en equipos críticos.'),

    ('REGISTRO-USO', 'Registro mensual de uso: sesiones, horas y usuarios por tipo y finalidad', 'ejecucion',
     'mensual', 'sistema', False, 'fin', 0, 'reservas', 10, '100 % de las sesiones registradas en la plataforma.'),
    ('PRACTICAS-FT02', 'FT02 · Planificación de cada práctica', 'ejecucion', 'semestral', 'sistema', False,
     'fin', 0, 'planificaciones', 20, ''),
    ('PRACTICAS-FT03', 'FT03 · Registro de ejecución con asistencia, bitácora y evidencias', 'ejecucion',
     'semestral', 'sistema', False, 'fin', 0, 'ejecuciones', 30, ''),
    ('GUIAS', 'Guías de práctica aprobadas y su vínculo con el syllabus', 'ejecucion', 'semestral', 'sistema',
     False, 'fin', 0, 'guias', 40, 'Al menos una guía nueva o actualizada por semestre.'),
    ('PRESTAMOS-EQUIPOS', 'Registro de préstamos de equipos', 'ejecucion', 'semestral', 'unidad', False,
     'fin', 0, '', 50, 'Quién retira, cuándo, para qué actividad y cuándo devuelve, con el estado del equipo.'),
    ('CHEQUEO-SEGURIDAD', 'Lista de chequeo de seguridad, bioseguridad e inocuidad', 'ejecucion', 'mensual',
     'unidad', False, 'fin', 0, '', 60, 'Aplicada al menos una vez al mes.'),
    ('INDUCCION-SEGURIDAD', 'Registro de inducción de seguridad a usuarios nuevos', 'ejecucion', 'semestral',
     'sistema', False, 'fin', 0, 'seguridad', 70, ''),
    ('DESECHOS', 'Registro de desechos peligrosos y especiales', 'ejecucion', 'semestral', 'sistema', False,
     'fin', 0, 'desechos', 80, ''),

    ('INFORME-SEMESTRAL', 'Informe semestral de actividades (firmado)', 'evaluacion', 'semestral', 'unidad',
     True, 'fin', 0, '', 10, 'Informe I (enero–junio) e Informe II (julio–diciembre), con anexos y evidencias.'),
    ('INDICADORES-PLAN', 'Plan semestral de prácticas frente a lo realizado', 'evaluacion', 'semestral',
     'sistema', False, 'fin', 0, 'asignaturas', 20, ''),
    ('INVENTARIO-CORTE', 'Inventario de equipos, software y espacios (corte semestral)', 'evaluacion',
     'semestral', 'sistema', False, 'fin', 0, 'recursos', 30, 'Dos cortes al año con altas, bajas y fuera de servicio.'),
    ('EQUIPAMIENTO', 'Equipamiento: disponibilidad y funcionalidad del período', 'evaluacion', 'semestral',
     'sistema', False, 'fin', 0, 'equipamiento', 40, ''),

    ('ACCIONES-MEJORA', 'Acciones de mejora del período', 'mejora', 'semestral', 'unidad', False, 'fin', 0, '',
     10, 'Hallazgo, acción, responsable, plazo, estado y evidencia.'),
)


def sembrar(apps, schema_editor):
    DocumentoExigido = apps.get_model('webcitt', 'DocumentoExigido')
    for (codigo, nombre, carpeta, periodicidad, origen, firma, regla, dias, fuente, orden, descripcion) in DOCUMENTOS:
        DocumentoExigido.objects.get_or_create(codigo=codigo, defaults={
            'nombre': nombre, 'carpeta': carpeta, 'periodicidad': periodicidad, 'origen': origen,
            'requiere_firma': firma, 'plazo_regla': regla, 'plazo_dias': dias, 'fuente_reporte': fuente,
            'orden': orden, 'descripcion': descripcion, 'tipos_unidad': [], 'activo': True,
        })


def retirar(apps, schema_editor):
    DocumentoExigido = apps.get_model('webcitt', 'DocumentoExigido')
    DocumentoExigido.objects.filter(codigo__in=[fila[0] for fila in DOCUMENTOS], documentos__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0210_expediente_de_calidad'),
    ]

    operations = [
        migrations.RunPython(sembrar, retirar),
    ]
