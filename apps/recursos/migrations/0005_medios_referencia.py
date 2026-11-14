from django.db import migrations, models
import apps.recursos.models.medios


class Migration(migrations.Migration):
    dependencies = [('recursos', '0004_diagnostico_reparacion_equipos')]
    operations = [
        migrations.AddField(
            model_name='equiposservicios', name='medios_referencia',
            field=models.JSONField(blank=True, default=dict, validators=[apps.recursos.models.medios.validar_medios_referencia],
                help_text='Procedencia, documentación y medios del modelo; la identificación física de cada activo se verifica aparte.'),
        ),
        migrations.AddField(
            model_name='softwaredisponible', name='medios_referencia',
            field=models.JSONField(blank=True, default=dict, validators=[apps.recursos.models.medios.validar_medios_referencia],
                help_text='Fuentes, créditos, guías y videos del producto identificado; no acredita instalaciones ni licencias.'),
        ),
        migrations.AddField(
            model_name='consumible', name='medios_referencia',
            field=models.JSONField(blank=True, default=dict, validators=[apps.recursos.models.medios.validar_medios_referencia],
                help_text='Fuentes y medios de la variante identificada; no acredita stock, compatibilidad ni recepción.'),
        ),
    ]
