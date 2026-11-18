"""El reglamento de uso de la unidad pasa a ser un documento principal permanente.

- Crea el exigido REGLAMENTO-USO junto a la resolución de creación y el protocolo, con la misma
  definición que ``expediente_catalogo.CATALOGO``. No toca ningún otro exigido.
- En cada unidad que ya preparó su expediente, agrega la fila del reglamento al último año preparado,
  con las mismas fechas que su protocolo, para que se pueda redactar sin volver a preparar el expediente.
  Los años anteriores lo muestran proyectado, como cualquier obligación nueva.

En una base vacía no hace nada: ``asegurar_catalogo`` siembra el catálogo completo. Se puede aplicar más
de una vez. Al revertir, el exigido se borra si nadie trabajó en él y, si no, queda inactivo.
"""
from django.db import migrations
from django.db.models import Max

CODIGO = 'REGLAMENTO-USO'
DEFINICION = dict(
    nombre='Reglamento de uso de la unidad', carpeta='planeacion', periodicidad='unica', origen='ambos',
    requiere_firma=True, condicional=False, plazo_regla='ninguno', plazo_dias=0, fuente_reporte='reglamento',
    orden=18, tipos_unidad=[], activo=True,
    descripcion=('Se elabora con el editor de la unidad sobre un texto estándar que solo cambia por tipo de unidad: '
                 'usuarios, horario y reservas, acceso y conducta, uso de los recursos, seguridad, responsabilidades y '
                 'contacto. Se envía y aprueba en la plataforma con QR; al enviarse se publica en la página de la unidad. '
                 'Cumplimiento obligatorio: la Dirección confirma su conformidad una vez por versión; no se califica.'),
)


def agregar_reglamento(apps, schema_editor):
    exigido_modelo = apps.get_model('documentos', 'DocumentoExigido')
    expediente = apps.get_model('documentos', 'DocumentoExpediente')
    alias = schema_editor.connection.alias
    if not exigido_modelo.objects.using(alias).exists():
        return
    reglamento, _ = exigido_modelo.objects.using(alias).get_or_create(codigo=CODIGO, defaults=DEFINICION)
    protocolos = expediente.objects.using(alias).filter(
        exigido__codigo='PROTOCOLO-BIOSEGURIDAD', corte='', mes__isnull=True)
    ultimos = dict(protocolos.values('unidad_id').annotate(anio=Max('anio')).values_list('unidad_id', 'anio'))
    for protocolo in protocolos.order_by('unidad_id', 'anio'):
        if ultimos.get(protocolo.unidad_id) != protocolo.anio:
            continue
        expediente.objects.using(alias).get_or_create(
            unidad_id=protocolo.unidad_id, exigido=reglamento, anio=protocolo.anio, corte='', mes=None,
            defaults=dict(abre_el=protocolo.abre_el, vence_el=protocolo.vence_el, tramo_inicio=protocolo.tramo_inicio,
                          tramo_fin=protocolo.tramo_fin, marco_periodo=protocolo.marco_periodo))


def retirar_reglamento(apps, schema_editor):
    exigido_modelo = apps.get_model('documentos', 'DocumentoExigido')
    expediente = apps.get_model('documentos', 'DocumentoExpediente')
    alias = schema_editor.connection.alias
    reglamento = exigido_modelo.objects.using(alias).filter(codigo=CODIGO).first()
    if reglamento is None:
        return
    filas = expediente.objects.using(alias).filter(exigido=reglamento)
    redactado = apps.get_model('documentos', 'DocumentoElaborado').objects.using(alias).filter(documento__in=filas)
    if filas.exclude(estado='pendiente').exists() or filas.filter(version__gt=0).exists() or redactado.exists():
        reglamento.activo = False
        reglamento.save(update_fields=['activo'])
        return
    filas.delete()
    reglamento.delete()


class Migration(migrations.Migration):
    dependencies = [('documentos', '0030_simulacro_como_evidencia_de_gestion')]
    operations = [migrations.RunPython(agregar_reglamento, retirar_reglamento)]
