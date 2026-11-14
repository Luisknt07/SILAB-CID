"""Los mantenimientos de ejemplo quedan a las nueve de la mañana, hora local.

La migración 0219 construyó sus fechas en UTC, así que en el calendario y en
la trazabilidad aparecían a las cuatro de la madrugada: una hora a la que la
unidad no interviene ningún equipo. Aquí se llevan a las 09:00 locales
conservando el día y lo que duró cada una, y su cierre de agenda se mueve con
ellas.

Solo alcanza a las órdenes que sembró 0219, identificadas por su título.
"""

from datetime import datetime, time, timedelta

from django.db import migrations
from django.utils import timezone

HORA_DE_TRABAJO = time(9, 0)

TITULOS = (
    'Reemplazo de la lámina PEI rayada',
    'Cambio de boquilla obstruida',
    'Limpieza mensual y tensión de correas',
    'Cambio de película FEP del tanque',
    'Alineación del tubo y reemplazo de la lente de enfoque',
    'Calibración de ejes y lubricación de guías',
    'Reemplazo del extrusor cubierto por la garantía',
)


def _local(dia, hora):
    return timezone.make_aware(datetime.combine(dia, hora), timezone.get_current_timezone())


def corregir(apps, schema_editor):
    MantenimientoEquipo = apps.get_model('webcitt', 'MantenimientoEquipo')
    BloqueoAgendaUnidad = apps.get_model('webcitt', 'BloqueoAgendaUnidad')

    hoy = timezone.localdate()
    for orden in MantenimientoEquipo.objects.filter(titulo__in=TITULOS):
        programada = timezone.localtime(orden.fecha_programada)
        duracion = timedelta(hours=orden.duracion_horas or 2)
        if orden.fecha_inicio and orden.fecha_fin:
            duracion = orden.fecha_fin - orden.fecha_inicio
        inicio = _local(programada.date(), HORA_DE_TRABAJO)
        orden.fecha_programada = inicio
        if orden.fecha_inicio:
            orden.fecha_inicio = inicio
        if orden.fecha_fin:
            orden.fecha_fin = inicio + duracion
        orden.duracion_horas = max(int(duracion.total_seconds() // 3600) or 1, 1)
        orden.save(update_fields=[
            'fecha_programada', 'fecha_inicio', 'fecha_fin', 'duracion_horas'])

        fin = timezone.localtime(orden.fecha_fin) if orden.fecha_fin else inicio + duracion
        if fin.date() != inicio.date():
            fin = inicio.replace(hour=23, minute=59)
        BloqueoAgendaUnidad.objects.filter(mantenimiento=orden).update(
            fecha_inicio=inicio.date(),
            fecha_fin=inicio.date(),
            hora_inicio=inicio.time(),
            hora_fin=fin.time(),
            activo=orden.estado != 'completado' or inicio.date() >= hoy,
        )


def retirar(apps, schema_editor):
    """La hora anterior no aportaba nada: no se restaura una madrugada."""


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0221_cierre_de_agenda_de_las_ordenes_sembradas'),
    ]

    operations = [
        migrations.RunPython(corregir, retirar),
    ]
