"""Las publicaciones pasan a ser un tipo de resultado: el centro produce publicaciones, datos, software, métodos,
tesis, prototipos y propiedad intelectual, y todos se registran igual, ligados a su proyecto, sus autores y su área."""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('centros_id', '0002_dominio_del_centro'),
    ]

    operations = [
        migrations.RenameModel(old_name='Publicacion', new_name='Resultado'),
        migrations.AlterModelOptions(
            name='resultado',
            options={'ordering': ('centro', '-anio', 'titulo'), 'verbose_name': 'Resultado',
                     'verbose_name_plural': 'Producción y resultados'},
        ),
    ]
