"""Índices aditivos para bandejas por centro, estado y solicitante."""
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False
    dependencies = [('centros_id', '0014_alter_centroid_area')]
    operations = [
        AddIndexConcurrently(model_name='solicitudcentro', index=models.Index(
            fields=('centro', 'estado', '-creada'), name='cid_solic_centro_estado_idx')),
        AddIndexConcurrently(model_name='solicitudcentro', index=models.Index(
            fields=('centro', 'usuario', '-creada'), name='cid_solic_centro_usuario_idx')),
    ]
