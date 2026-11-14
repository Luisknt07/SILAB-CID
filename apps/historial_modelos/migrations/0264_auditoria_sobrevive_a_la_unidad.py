"""La auditoría sobrevive a la unidad: guarda su nombre y no impide eliminarla.

Hasta ahora el registro de auditoría protegía a la unidad contra el borrado; una unidad de
prueba con tres registros no se podía eliminar. Ahora cada registro conserva el nombre de la
unidad al momento de crearse y, si la unidad se elimina, queda como histórico con ese nombre.
Se agrega la acción «eliminar» para dejar constancia de la baja.
"""
from django.db import migrations, models
from django.db.models import OuterRef, Subquery
import django.db.models.deletion


def guardar_nombres(apps, schema_editor):
    Registro = apps.get_model('webcitt', 'RegistroAuditoriaUnidad')
    Unidad = apps.get_model('webcitt', 'Unidad')
    Registro.objects.filter(unidad__isnull=False, unidad_nombre='').update(
        unidad_nombre=Subquery(Unidad.objects.filter(pk=OuterRef('unidad_id')).values('nombre')[:1]))


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0263_nombre_corto_y_area_gestion'),
    ]

    operations = [
        migrations.AddField(
            model_name='registroauditoriaunidad',
            name='unidad_nombre',
            field=models.CharField(blank=True, editable=False, max_length=200),
        ),
        migrations.AlterField(
            model_name='registroauditoriaunidad',
            name='accion',
            field=models.CharField(choices=[('crear', 'Crear'), ('actualizar', 'Actualizar'), ('enviar', 'Enviar a revisión'), ('aprobar', 'Aprobar o validar'), ('observar', 'Observar'), ('archivar', 'Archivar'), ('consultar', 'Consultar'), ('descargar', 'Descargar'), ('eliminar', 'Eliminar')], db_index=True, max_length=15),
        ),
        migrations.AlterField(
            model_name='registroauditoriaunidad',
            name='unidad',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='auditoria_operativa', to='webcitt.unidad'),
        ),
        migrations.RunPython(guardar_nombres, migrations.RunPython.noop),
    ]
