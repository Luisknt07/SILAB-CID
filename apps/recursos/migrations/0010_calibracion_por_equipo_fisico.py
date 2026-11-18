"""Calibración por equipo físico.

Cada equipo físico tiene su última y próxima calibración y su certificado. En la migración cada equipo recibe las
fechas que hoy tiene su modelo (las mismas que mostraba); el certificado queda vacío, porque el modelo no guardaba
ninguno. Las fechas del modelo se conservan como valor de referencia.
"""
from django.db import migrations, models


def fechas_del_modelo_a_sus_equipos(apps, schema_editor):
    EquiposServicios = apps.get_model('recursos', 'EquiposServicios')
    UnidadEquipo = apps.get_model('recursos', 'UnidadEquipo')
    modelos = (EquiposServicios.objects
               .filter(models.Q(fecha_ultima_calibracion__isnull=False) | models.Q(proxima_calibracion__isnull=False))
               .values_list('pk', 'fecha_ultima_calibracion', 'proxima_calibracion'))
    for modelo_id, ultima, proxima in modelos.iterator():
        UnidadEquipo.objects.filter(equipo_id=modelo_id).update(ultima_calibracion=ultima, proxima_calibracion=proxima)


class Migration(migrations.Migration):

    dependencies = [
        ('recursos', '0009_incidentes_de_seguridad_sin_equipo'),
    ]

    operations = [
        migrations.AddField(
            model_name='unidadequipo',
            name='ultima_calibracion',
            field=models.DateField(blank=True, null=True, verbose_name='Última calibración'),
        ),
        migrations.AddField(
            model_name='unidadequipo',
            name='proxima_calibracion',
            field=models.DateField(blank=True, help_text='Con estas fechas el equipo sale en «Calibración de equipos» del Centro de reportes.', null=True, verbose_name='Próxima calibración'),
        ),
        migrations.AddField(
            model_name='unidadequipo',
            name='certificado_calibracion',
            field=models.FileField(blank=True, help_text='PDF o imagen del último certificado. Al completar una orden de calibración se toma su informe.', upload_to='equipos/calibraciones/', verbose_name='Certificado de calibración'),
        ),
        migrations.RunPython(fechas_del_modelo_a_sus_equipos, migrations.RunPython.noop),
    ]
