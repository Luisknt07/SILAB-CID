from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('documentos', '0014_aprobacion_documental_en_linea')]
    operations = [
        migrations.AddField(model_name='constanciadocumento', name='archivo_aprobado',
            field=models.FileField(blank=True, editable=False, upload_to='documentos/aprobaciones/')),
        migrations.AddField(model_name='constanciadocumento', name='sha256_aprobado',
            field=models.CharField(blank=True, editable=False, max_length=64)),
    ]
