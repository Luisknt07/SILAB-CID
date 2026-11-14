from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('documentos', '0003_plazo_correccion')]

    operations = [
        migrations.AddField(
            model_name='evidenciagestionunidad', name='detalle',
            field=models.JSONField(blank=True, default=dict,
                help_text='Resultado, aceptación o inspección documentada con su alcance y seguimiento.')),
        migrations.AlterField(
            model_name='evidenciagestionunidad', name='tipo',
            field=models.CharField(max_length=20, choices=[
                ('USO', 'Conciliación de sesiones observadas'),
                ('DESECHOS', 'Conciliación de partidas de desechos generadas'),
                ('INVENTARIO', 'Acta de revisión de equipos, software y espacios'),
                ('CAPACITACION', 'Capacitación recibida por el personal'),
                ('DIFUSION', 'Publicación, evento o material difundido'),
                ('INVESTIGACION', 'Resultado de investigación o desarrollo tecnológico'),
                ('TRANSFERENCIA', 'Transferencia o servicio especializado aceptado'),
                ('INSPECCION', 'Inspección de seguridad y condiciones de operación'),
                ('BOLETINES', 'Boletín o informe publicado'), ('EVENTOS', 'Evento realizado'),
                ('PROYECTOS', 'Proyecto de investigación en ejecución'),
                ('PUBLICACIONES', 'Artículo o ponencia publicados'),
                ('ENSAYOS', 'Ensayo establecido y evaluado'), ('PRODUCCION', 'Proceso o lote cerrado')]))]
