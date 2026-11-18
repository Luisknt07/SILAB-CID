"""Incidentes de seguridad sin equipo y con la fecha del hecho.

El equipo pasa a ser opcional (el modelo lo sigue exigiendo salvo en los incidentes de seguridad), se agrega el
espacio de la unidad donde ocurrió y la fecha y hora del hecho. En las filas existentes la fecha del hecho es la del
reporte, que era la única que se registraba; nada más cambia. La unidad ya se guardaba en cada incidencia.
"""
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


def fecha_del_hecho_desde_el_reporte(apps, schema_editor):
    IncidenciaEquipo = apps.get_model('recursos', 'IncidenciaEquipo')
    IncidenciaEquipo.objects.filter(fecha_hecho__isnull=True).update(fecha_hecho=models.F('fecha_reporte'))
    if schema_editor is not None and schema_editor.connection.vendor == 'postgresql':
        # Cierra aquí las comprobaciones diferidas antes de volver obligatoria la columna.
        schema_editor.execute('SET CONSTRAINTS ALL IMMEDIATE')


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_unidades', '0006_personal_formacion_y_designacion'),
        ('recursos', '0008_sustancias_controladas'),
    ]

    operations = [
        migrations.AlterField(
            model_name='incidenciaequipo',
            name='equipo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='incidencias', to='recursos.unidadequipo'),
        ),
        migrations.AddField(
            model_name='incidenciaequipo',
            name='espacio',
            field=models.ForeignKey(blank=True, help_text='Lugar del incidente de seguridad cuando no involucra un equipo.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='incidencias_seguridad', to='gestion_unidades.espacioreservable'),
        ),
        migrations.AddField(
            model_name='incidenciaequipo',
            name='fecha_hecho',
            field=models.DateTimeField(null=True, verbose_name='Fecha y hora del hecho'),
        ),
        migrations.RunPython(fecha_del_hecho_desde_el_reporte, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='incidenciaequipo',
            name='fecha_hecho',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Cuándo ocurrió; por omisión, cuando se reporta. No puede ser futura.', verbose_name='Fecha y hora del hecho'),
        ),
    ]
