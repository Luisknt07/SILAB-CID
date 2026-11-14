"""Las órdenes ya registradas también toman su equipo en el calendario.

El cierre de agenda lo crea la orden al guardarse, pero las órdenes que
existían antes —y las que sembró la migración 0219, que escribe sin pasar por
la lógica del modelo— quedaron sin él. Aquí se les genera con la misma regla,
para que el calendario cuente la misma historia que el seguimiento.

No se toca ninguna orden cancelada ni ninguna que ya tenga su cierre.
"""

from datetime import timedelta

from django.db import migrations
from django.utils import timezone

DURACION_POR_OMISION = 2


def _ventana(orden):
    """(día, hora de inicio, hora de fin) que ocupó o va a ocupar el equipo."""
    if not orden.fecha_programada:
        return None
    inicio = timezone.localtime(orden.fecha_inicio or orden.fecha_programada)
    fin = timezone.localtime(orden.fecha_fin) if orden.fecha_fin else None
    if not fin or fin <= inicio or fin.date() != inicio.date():
        fin = inicio + timedelta(hours=max(orden.duracion_horas or DURACION_POR_OMISION, 1))
    if fin.date() != inicio.date():
        fin = inicio.replace(hour=23, minute=59)
    return inicio.date(), inicio.time(), fin.time()


def sembrar(apps, schema_editor):
    MantenimientoEquipo = apps.get_model('webcitt', 'MantenimientoEquipo')
    BloqueoAgendaUnidad = apps.get_model('webcitt', 'BloqueoAgendaUnidad')

    hoy = timezone.localdate()
    pendientes = (MantenimientoEquipo.objects
                  .filter(bloquea_agenda=True, bloqueo_agenda__isnull=True,
                          unidad__isnull=False)
                  .exclude(estado='cancelado')
                  .select_related('equipo'))
    for orden in pendientes:
        ventana = _ventana(orden)
        if not ventana:
            continue
        dia, desde, hasta = ventana
        bloqueo = BloqueoAgendaUnidad.objects.create(
            unidad_id=orden.unidad_id,
            mantenimiento=orden,
            tipo='mantenimiento',
            titulo=f'{orden.codigo} · {orden.titulo}'[:160],
            motivo=orden.descripcion or '',
            fecha_inicio=dia,
            fecha_fin=dia,
            dia_completo=False,
            hora_inicio=desde,
            hora_fin=hasta,
            alcance='equipos',
            bloquea_recursos=True,
            bloquea_servicios=True,
            visible_en_agenda=True,
            activo=orden.estado != 'completado' or dia >= hoy,
        )
        bloqueo.equipos.set([orden.equipo_id])


def retirar(apps, schema_editor):
    BloqueoAgendaUnidad = apps.get_model('webcitt', 'BloqueoAgendaUnidad')
    BloqueoAgendaUnidad.objects.filter(mantenimiento__isnull=False).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0220_orden_bloquea_la_agenda'),
    ]

    operations = [
        migrations.RunPython(sembrar, retirar),
    ]
