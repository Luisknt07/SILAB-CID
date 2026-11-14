"""Índices aditivos de aforo, sin bloquear escrituras en PostgreSQL."""
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False
    dependencies = [('webcitt', '0325_formacion_lateral_certificados')]
    operations = [
        AddIndexConcurrently(model_name='inscripcioncurso', index=models.Index(
            fields=('edicion', 'estado'), name='curso_insc_edicion_estado_idx')),
        AddIndexConcurrently(model_name='invitacioncurso', index=models.Index(
            fields=('edicion', 'activa'), name='curso_invit_edicion_activa_idx')),
    ]
