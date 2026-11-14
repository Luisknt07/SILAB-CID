"""El catálogo exigido, ajustado a lo que de verdad se audita.

La planificación y el informe son semestrales, se redactan con el editor
guiado y se firman. Organigrama y manual de funciones ya no son documentos
aparte: son la sección «Estructura orgánica-funcional» de la planificación.
Los registros que el sistema produce solos dejan de contarse como entregas
de la unidad, y lo que no todas las unidades hacen queda «cuando aplique».
"""

from django.db import migrations

CAMBIOS = {
    'PLANIFICACION-ANUAL': {
        'codigo': 'PLANIFICACION',
        'nombre': 'Planificación semestral de la unidad (firmada)',
        'periodicidad': 'semestral', 'origen': 'ambos', 'requiere_firma': True,
        'plazo_regla': 'inicio', 'plazo_dias': 15, 'fuente_reporte': 'planificacion', 'orden': 20,
        'descripcion': 'Se redacta con el editor guiado: el sistema llena lo que ya sabe (datos de la unidad, '
                       'espacios, servicios, inventario) y la unidad completa misión, objetivos, diagnóstico, plan '
                       'de actividades e inversión. El PDF se firma y se carga en los primeros quince días del período.',
    },
    'ORGANIGRAMA': {'activo': False},
    'MANUAL-FUNCIONES': {'activo': False},
    'PLAN-MANTENIMIENTO': {'condicional': True},
    'REGISTRO-USO': {
        'nombre': 'Registro de uso del período: sesiones, horas y usuarios por tipo y finalidad',
        'periodicidad': 'semestral',
        'descripcion': 'Lo produce el sistema con las reservas registradas; el 100 % de las sesiones debe pasar '
                       'por la plataforma.',
    },
    'PRACTICAS-FT02': {'condicional': True},
    'PRACTICAS-FT03': {'condicional': True},
    'GUIAS': {'condicional': True},
    'PRESTAMOS-EQUIPOS': {'condicional': True},
    'CHEQUEO-SEGURIDAD': {
        'nombre': 'Listas de chequeo de seguridad, bioseguridad e inocuidad del período',
        'periodicidad': 'semestral', 'condicional': True,
        'descripcion': 'Una lista por mes, consolidadas en un solo archivo por período. Solo cuando aplique.',
    },
    'INDUCCION-SEGURIDAD': {'condicional': True},
    'DESECHOS': {'condicional': True},
    'INFORME-SEMESTRAL': {
        'origen': 'ambos', 'requiere_firma': True, 'fuente_reporte': 'informe',
        'descripcion': 'Se redacta con el editor guiado sobre lo que el sistema registró en el período: cumplimiento '
                       'del plan, uso, logros, dificultades y acciones de mejora. Se firma y se carga antes del cierre.',
    },
    'INDICADORES-PLAN': {'condicional': True},
    'ACCIONES-MEJORA': {
        'origen': 'sistema', 'fuente_reporte': 'mejora', 'requiere_firma': False,
        'nombre': 'Seguimiento de acciones de mejora',
        'descripcion': 'Se consolida desde las acciones registradas en los informes semestrales: hallazgo, acción, '
                       'responsable, plazo y estado.',
    },
}

REVERSO = {
    'PLANIFICACION': {
        'codigo': 'PLANIFICACION-ANUAL', 'nombre': 'Planificación anual de la unidad (firmada)',
        'periodicidad': 'anual', 'origen': 'unidad', 'fuente_reporte': '',
    },
    'ORGANIGRAMA': {'activo': True},
    'MANUAL-FUNCIONES': {'activo': True},
    'REGISTRO-USO': {'periodicidad': 'mensual'},
    'CHEQUEO-SEGURIDAD': {'periodicidad': 'mensual'},
    'INFORME-SEMESTRAL': {'origen': 'unidad', 'fuente_reporte': ''},
    'ACCIONES-MEJORA': {'origen': 'unidad', 'fuente_reporte': '', 'nombre': 'Acciones de mejora del período'},
}


def ajustar(apps, schema_editor):
    DocumentoExigido = apps.get_model('webcitt', 'DocumentoExigido')
    DocumentoExpediente = apps.get_model('webcitt', 'DocumentoExpediente')
    for codigo, valores in CAMBIOS.items():
        DocumentoExigido.objects.filter(codigo=codigo).update(**valores)
    # Las filas que cambiaron de periodicidad y aún no tienen archivo se vuelven a
    # materializar con el nuevo tramo; las que ya guardan algo se conservan.
    DocumentoExpediente.objects.filter(
        exigido__codigo__in=('PLANIFICACION', 'REGISTRO-USO', 'CHEQUEO-SEGURIDAD'),
        estado='pendiente', recurso__isnull=True,
    ).delete()


def revertir(apps, schema_editor):
    DocumentoExigido = apps.get_model('webcitt', 'DocumentoExigido')
    for codigo, valores in REVERSO.items():
        DocumentoExigido.objects.filter(codigo=codigo).update(**valores)


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0212_planificacion_e_informe_redactados'),
    ]

    operations = [
        migrations.RunPython(ajustar, revertir),
    ]
