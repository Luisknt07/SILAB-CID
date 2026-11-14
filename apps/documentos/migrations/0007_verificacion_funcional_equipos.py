from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('documentos', '0006_mantenimiento_infraestructura')]

    operations = [migrations.AlterField(
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
            ('PLAN-INFRA', 'Plan de mantenimiento de infraestructura'),
            ('EJECUCION-INFRA', 'Informe de ejecución del mantenimiento de infraestructura'),
            ('FUNCIONALIDAD', 'Verificación funcional documentada de equipos'),
            ('BOLETINES', 'Boletín o informe publicado'), ('EVENTOS', 'Evento realizado'),
            ('PROYECTOS', 'Proyecto de investigación en ejecución'),
            ('PUBLICACIONES', 'Artículo o ponencia publicados'),
            ('ENSAYOS', 'Ensayo establecido y evaluado'), ('PRODUCCION', 'Proceso o lote cerrado')]))]
