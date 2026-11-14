from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('webcitt', '0312_gestion_productiva_de_los_centros')]
    operations = [migrations.CreateModel(
        name='ContadorPeticion',
        fields=[
            ('clave', models.CharField(max_length=64, primary_key=True, serialize=False)),
            ('total', models.PositiveIntegerField(default=1)),
            ('vence', models.DateTimeField(db_index=True)),
        ],
        options={'verbose_name': 'Contador temporal de peticiones'},
    )]
