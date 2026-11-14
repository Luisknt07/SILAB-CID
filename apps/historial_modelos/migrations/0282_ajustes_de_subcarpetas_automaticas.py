from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0281_repuestos_del_modelo'),
    ]

    operations = [
        migrations.AddField(
            model_name='ajusteseccionplanta',
            name='grupos',
            field=models.JSONField(blank=True, default=dict, help_text='Por subcarpeta automática (cada área en las fichas de equipo, el escáner…): nombre propio, orden y si está oculta.', verbose_name='Subcarpetas automáticas'),
        ),
        migrations.AddField(
            model_name='ajusteseccionplanta',
            name='elementos_ocultos',
            field=models.JSONField(blank=True, default=list, help_text='Los elementos automáticos que la unidad retiró del menú; el registro se conserva.', verbose_name='Elementos ocultos'),
        ),
    ]
