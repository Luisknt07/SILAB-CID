from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('directorio_unidades', '0001_propiedad_modelos')]
    operations = [
        migrations.AddField(model_name='dependenciaacademica', name='centro_costo',
            field=models.CharField('Centro de costo agrupador', max_length=220, blank=True,
                help_text='Denominación confirmada para la matriz universitaria de compras. '
                          'La dependencia administra este centro y ejecuta las adquisiciones autorizadas.')),
        migrations.AlterField(model_name='unidad', name='adscrita_a',
            field=models.ForeignKey('directorio_unidades.dependenciaacademica', on_delete=models.SET_NULL,
                null=True, blank=True, related_name='unidades', verbose_name='Adscrita a',
                help_text='Decanato o dependencia que recibe los resultados evaluados por Dirección y gestiona sus compras.')),
    ]
