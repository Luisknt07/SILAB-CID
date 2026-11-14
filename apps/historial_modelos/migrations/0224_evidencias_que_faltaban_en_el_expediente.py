"""Cuatro evidencias que la unidad producía pero no llegaban al expediente.

La auditoría pide ocho informes. Siete ya se archivaban; investigación,
transferencia y el corte de insumos se podían consultar en el Centro de
reportes pero no contaban como entrega, así que nadie los exigía ni se les
vencía el plazo. El registro de préstamos sí se exigía, pero cargado a mano,
porque hasta ahora el préstamo solo era la marca «prestado» en el activo.

Los cuatro pasan a salir del sistema, con su reporte detrás. Los tres nuevos
son condicionales: una unidad que no recibió investigación en el período no
incumple, le consta «no aplica».
"""

from django.db import migrations

# codigo, nombre, carpeta, periodicidad, fuente, orden, descripcion
NUEVOS = (
    ('INSUMOS-CORTE', 'Reactivos e insumos: existencias y movimientos del período', 'evaluacion',
     'semestral', 'inventario', 50,
     'El inventario de equipos corta aparte; este cubre lo que se consume. Solo cuando la unidad '
     'lleva insumos.'),
    ('INVESTIGACION', 'Investigación aplicada y desarrollo tecnológico en la unidad', 'evaluacion',
     'semestral', 'investigacion', 60,
     'Uso de la unidad para investigación, desarrollo y titulación, con su responsable y sus horas. '
     'Solo cuando la unidad recibió trabajos de investigación en el período.'),
    ('TRANSFERENCIA', 'Transferencia de conocimiento y servicios a la sociedad', 'evaluacion',
     'semestral', 'transferencia', 70,
     'Servicios prestados, vinculación y capacitación, con su beneficiario. Solo cuando la unidad '
     'prestó servicios o hizo vinculación en el período.'),
)

PRESTAMOS = (
    'Quién retira, cuándo, para qué actividad y cuándo devuelve, con el estado del equipo. '
    'Sale de los préstamos registrados en la consola; el externo además exige su acta.'
)


def sembrar(apps, schema_editor):
    DocumentoExigido = apps.get_model('webcitt', 'DocumentoExigido')
    if not DocumentoExigido.objects.exists():
        # Base vacía: el catálogo completo se siembra solo cuando haga falta.
        return
    for codigo, nombre, carpeta, periodicidad, fuente, orden, descripcion in NUEVOS:
        DocumentoExigido.objects.get_or_create(codigo=codigo, defaults={
            'nombre': nombre, 'carpeta': carpeta, 'periodicidad': periodicidad, 'origen': 'sistema',
            'requiere_firma': False, 'condicional': True, 'plazo_regla': 'fin', 'plazo_dias': 0,
            'fuente_reporte': fuente, 'orden': orden, 'descripcion': descripcion,
            'tipos_unidad': [], 'activo': True,
        })
    DocumentoExigido.objects.filter(codigo='PRESTAMOS-EQUIPOS').update(
        origen='sistema', fuente_reporte='prestamos', descripcion=PRESTAMOS)


def retirar(apps, schema_editor):
    DocumentoExigido = apps.get_model('webcitt', 'DocumentoExigido')
    DocumentoExigido.objects.filter(codigo__in=[codigo for codigo, *_ in NUEVOS]).delete()
    DocumentoExigido.objects.filter(codigo='PRESTAMOS-EQUIPOS').update(
        origen='unidad', fuente_reporte='',
        descripcion='Quién retira, cuándo, para qué actividad y cuándo devuelve, con el estado del equipo.')


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0223_registro_de_prestamos'),
    ]

    operations = [
        migrations.RunPython(sembrar, retirar),
    ]
